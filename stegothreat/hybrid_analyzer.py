import os
import yara
import requests
import logging
import hashlib
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()


class HybridThreatAnalyzer:
    def __init__(self):
        # ============================
        #  VIRUSTOTAL API KEY (from env)
        # ============================
        self.vt_api_key = os.getenv("VT_API_KEY", "")
        self.vt_base = "https://www.virustotal.com/api/v3"

        if not self.vt_api_key:
            logger.warning("⚠️ VT_API_KEY not set. VirusTotal integration disabled.")

        try:
            self.rules = yara.compile("yara_rules.yar")
            logger.info("✅ YARA rules loaded successfully")
        except Exception as e:
            logger.error(f"❌ YARA load failed: {e}")
            self.rules = None

    # ---------- YARA (local) ----------

    def yara_scan(self, text_payload: str):
        try:
            if not self.rules:
                return {"detected": False, "error": "YARA not loaded", "risk_score": 0}

            matches = self.rules.match(data=text_payload.encode("utf-8"))
            detections = []
            score = 0

            for match in matches:
                detections.append(
                    {
                        "rule": match.rule,
                        "meta": match.meta.get("description", "Unknown"),
                        "score": match.meta.get("score", 50),
                    }
                )
                score += match.meta.get("score", 50)

            logger.info(f"YARA found {len(matches)} matches")
            return {
                "detected": len(matches) > 0,
                "threats": detections,
                "risk_score": min(score, 100),
                "engines": f"{len(matches)} YARA rules",
            }
        except Exception as e:
            logger.error(f"YARA scan error: {e}")
            return {"detected": False, "error": str(e), "risk_score": 0}

    # ---------- VirusTotal v3 (submit + sha256 only) ----------

    def _vt_headers(self):
        return {
            "x-apikey": self.vt_api_key,
            "User-Agent": "stegothreat-demo",
        }

    def _payload_to_bytes(self, text_payload: str) -> bytes:
        return text_payload.encode("utf-8")

    def _sha256(self, data: bytes) -> str:
        h = hashlib.sha256()
        h.update(data)
        return h.hexdigest()

    def virustotal_v3(self, text_payload: str):
        """
        Upload payload bytes to VT v3 and return only status + sha256.
        No polling, no engine stats; UI will show link using sha256.
        """
        if not self.vt_api_key:
            return {"error": "No VT API key", "status": "error", "sha256": None}

        payload_bytes = self._payload_to_bytes(text_payload)
        sha256_hash = self._sha256(payload_bytes)

        files = {"file": ("payload.txt", payload_bytes)}
        url = f"{self.vt_base}/files"

        try:
            r = requests.post(url, headers=self._vt_headers(), files=files, timeout=20)
            logger.info(f"VT v3 /files status={r.status_code}")

            if r.status_code != 200:
                # We still return sha256 so the link works, but mark error
                return {
                    "status": "error",
                    "error": f"/files HTTP {r.status_code}",
                    "sha256": sha256_hash,
                    "raw": r.text[:200],
                }

            # We don’t need analysis id for the link; VT will process asynchronously.
            return {
                "status": "submitted",
                "sha256": sha256_hash,
            }
        except Exception as e:
            logger.error(f"VT upload error: {e}")
            return {"status": "error", "error": str(e), "sha256": sha256_hash}

    # ---------- Hybrid ----------

    def analyze(self, text_payload: str):
        logger.info(f"Analyzing payload ({len(text_payload)} chars)")

        yara_result = self.yara_scan(text_payload)
        vt_result = self.virustotal_v3(text_payload) if self.vt_api_key else None

        # Overall risk is driven by YARA only (VT is external confirmation)
        final_risk = yara_result["risk_score"]

        if final_risk == 0:
            status = "✅ Clean"
        elif final_risk <= 50:
            status = "⚠️ Suspicious"
        else:
            status = "🚨 CONFIRMED"

        logger.info(f"Final risk score: {final_risk}% ({status})")

        return {
            "detected": yara_result["detected"],
            "risk_score": final_risk,
            "yara": yara_result,
            "virustotal": vt_result,
            "status": status,
            "payload_length": len(text_payload),
        }
