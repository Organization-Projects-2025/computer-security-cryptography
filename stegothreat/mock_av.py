class MockAntivirus:
    def scan_image(self, image_path):
        """Always passes images as clean"""
        return {"clean": True, "threats": []}
    
    def scan_payload(self, payload_bytes):
        """Detects based on simple signatures"""
        payload_str = payload_bytes[:100].decode('utf-8', errors='ignore')
        
        signatures = {
            'reverse_shell': ['socket', 'connect', 'reverse'],
            'keylogger': ['keyboard', 'keylogger', 'hook'],
            'ransomware': ['encrypt', 'ransom']
        }
        
        detections = []
        for threat, sigs in signatures.items():
            for sig in sigs:
                if sig in payload_str.lower():
                    detections.append(threat)
        
        return {
            "clean": len(detections) == 0,
            "threats": detections,
            "confidence": len(detections) * 30
        }
