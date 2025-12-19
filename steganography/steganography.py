"""
Steganography Module - Hide and Extract Data in Images
Uses LSB (Least Significant Bit) technique to hide data in images
"""

from PIL import Image
import os


class Steganography:
    """Class for hiding and extracting data from images using LSB steganography"""

    @staticmethod
    def _string_to_binary(data):
        """Convert string to binary format"""
        if isinstance(data, str):
            return "".join([format(ord(char), "08b") for char in data])
        elif isinstance(data, bytes):
            return "".join([format(byte, "08b") for byte in data])

    @staticmethod
    def _binary_to_string(binary_data):
        """Convert binary data back to string"""
        chars = []
        for i in range(0, len(binary_data), 8):
            byte = binary_data[i : i + 8]
            chars.append(chr(int(byte, 2)))
        return "".join(chars)

    @staticmethod
    def hide_text_in_image(image_path, secret_text, output_path):
        """
        Hide text message in an image

        Args:
            image_path: Path to the cover image
            secret_text: Text message to hide
            output_path: Path to save the stego image

        Returns:
            True if successful, False otherwise
        """
        try:
            # Open the image
            img = Image.open(image_path)

            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Get image dimensions
            width, height = img.size

            # Add delimiter to mark end of message
            secret_text += "<<END>>"

            # Convert message to binary
            binary_message = Steganography._string_to_binary(secret_text)
            data_length = len(binary_message)

            # Check if image can hold the message
            max_bytes = width * height * 3  # 3 color channels
            if data_length > max_bytes:
                raise ValueError(
                    f"Image is too small to hide this message. Max capacity: {max_bytes} bits"
                )

            # Hide data in image
            data_index = 0
            pixels = img.load()

            for y in range(height):
                for x in range(width):
                    if data_index < data_length:
                        pixel = list(pixels[x, y])

                        # Modify RGB channels
                        for channel in range(3):
                            if data_index < data_length:
                                # Replace LSB with message bit
                                pixel[channel] = pixel[channel] & ~1 | int(
                                    binary_message[data_index]
                                )
                                data_index += 1

                        pixels[x, y] = tuple(pixel)
                    else:
                        break
                if data_index >= data_length:
                    break

            # Save the stego image
            img.save(output_path)
            return True

        except Exception as e:
            print(f"Error hiding text: {e}")
            return False

    @staticmethod
    def extract_text_from_image(image_path):
        """
        Extract hidden text from an image

        Args:
            image_path: Path to the stego image

        Returns:
            Extracted text message or None if error
        """
        try:
            # Open the image
            img = Image.open(image_path)

            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            width, height = img.size
            pixels = img.load()

            binary_message = ""

            # Extract LSBs from image
            for y in range(height):
                for x in range(width):
                    pixel = pixels[x, y]

                    for channel in range(3):
                        binary_message += str(pixel[channel] & 1)

            # Convert binary to string
            message = ""
            for i in range(0, len(binary_message), 8):
                byte = binary_message[i : i + 8]
                char = chr(int(byte, 2))
                message += char

                # Check for end delimiter
                if message.endswith("<<END>>"):
                    return message[:-7]  # Remove delimiter

            return message

        except Exception as e:
            print(f"Error extracting text: {e}")
            return None

    @staticmethod
    def hide_image_in_image(cover_image_path, secret_image_path, output_path):
        """
        Hide one image inside another image

        Args:
            cover_image_path: Path to the cover image
            secret_image_path: Path to the secret image to hide
            output_path: Path to save the stego image

        Returns:
            True if successful, False otherwise
        """
        try:
            # Open both images
            cover_img = Image.open(cover_image_path).convert("RGB")
            secret_img = Image.open(secret_image_path).convert("RGB")

            # Get dimensions
            cover_width, cover_height = cover_img.size
            secret_width, secret_height = secret_img.size

            # Check if secret image can fit in cover image
            if secret_width > cover_width or secret_height > cover_height:
                # Resize secret image to fit
                secret_img = secret_img.resize(
                    (min(secret_width, cover_width), min(secret_height, cover_height))
                )
                secret_width, secret_height = secret_img.size

            # Create a copy of cover image
            stego_img = cover_img.copy()
            cover_pixels = stego_img.load()
            secret_pixels = secret_img.load()

            # Encode secret image dimensions at the start
            dim_data = f"{secret_width}x{secret_height}<<DIM>>"
            binary_dim = Steganography._string_to_binary(dim_data)

            data_index = 0
            header_pixels_used = 0

            # Hide dimensions first in LSBs
            for y in range(cover_height):
                for x in range(cover_width):
                    if data_index < len(binary_dim):
                        pixel = list(cover_pixels[x, y])
                        for channel in range(3):
                            if data_index < len(binary_dim):
                                pixel[channel] = pixel[channel] & ~1 | int(
                                    binary_dim[data_index]
                                )
                                data_index += 1
                        cover_pixels[x, y] = tuple(pixel)
                        header_pixels_used += 1
                    else:
                        break
                if data_index >= len(binary_dim):
                    break

            print(f"Header stored in {header_pixels_used} pixels")

            # Calculate starting position for image data (skip header area)
            # Add some padding to ensure we don't overlap
            start_y = (header_pixels_used // cover_width) + 1
            start_x = 0

            # Hide secret image pixels (using 4 LSBs for better quality)
            # Start from position after header
            for sy in range(secret_height):
                for sx in range(secret_width):
                    secret_pixel = secret_pixels[sx, sy]

                    # Calculate position in cover image (offset by header size)
                    cx = sx + start_x
                    cy = sy + start_y

                    if cx < cover_width and cy < cover_height:
                        cover_pixel = list(cover_pixels[cx, cy])

                        # Hide 4 MSBs of secret in 4 LSBs of cover
                        for channel in range(3):
                            # Get 4 most significant bits from secret
                            secret_bits = (secret_pixel[channel] >> 4) & 0x0F
                            # Clear 4 LSBs of cover and set them to secret bits
                            cover_pixel[channel] = (
                                cover_pixel[channel] & 0xF0
                            ) | secret_bits

                        cover_pixels[cx, cy] = tuple(cover_pixel)

            # Save the stego image
            stego_img.save(output_path)
            print(f"Image hidden successfully: {secret_width}x{secret_height}")
            return True

        except Exception as e:
            import traceback

            print(f"Error hiding image: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def extract_image_from_image(stego_image_path, output_path):
        """
        Extract hidden image from a stego image

        Args:
            stego_image_path: Path to the stego image
            output_path: Path to save the extracted image

        Returns:
            True if successful, False otherwise
        """
        try:
            # Open the stego image
            stego_img = Image.open(stego_image_path).convert("RGB")
            width, height = stego_img.size
            pixels = stego_img.load()

            # Extract dimensions from LSBs (more efficient - only extract what we need)
            binary_message = ""
            max_header_bits = (
                500 * 8
            )  # Maximum expected header size in bits (increased for safety)
            bit_count = 0
            found_delimiter = False
            secret_width = 0
            secret_height = 0
            header_pixels_used = 0

            for y in range(height):
                for x in range(width):
                    if bit_count >= max_header_bits:
                        break
                    pixel = pixels[x, y]
                    for channel in range(3):
                        binary_message += str(pixel[channel] & 1)
                        bit_count += 1

                        # Check every 8 bits if we have the delimiter
                        if bit_count % 8 == 0 and bit_count >= 64:  # Minimum size check
                            try:
                                temp_msg = ""
                                for i in range(0, len(binary_message), 8):
                                    byte = binary_message[i : i + 8]
                                    if len(byte) == 8:
                                        byte_val = int(byte, 2)
                                        if (
                                            byte_val < 128
                                        ):  # Valid ASCII range for header
                                            temp_msg += chr(byte_val)
                                        else:
                                            temp_msg += "?"
                                if "<<DIM>>" in temp_msg:
                                    dim_str = temp_msg.split("<<DIM>>")[0]
                                    secret_width, secret_height = map(
                                        int, dim_str.split("x")
                                    )
                                    found_delimiter = True
                                    header_pixels_used = (
                                        bit_count + 2
                                    ) // 3  # Calculate pixels used
                                    break
                            except (ValueError, IndexError):
                                # Continue searching if parsing fails
                                pass
                    if found_delimiter:
                        header_pixels_used = y * width + x + 1
                        break
                if found_delimiter:
                    break

            if not found_delimiter:
                raise ValueError(
                    "Could not find dimension header in image. This may not be a valid stego image with a hidden image."
                )

            print(f"Found hidden image dimensions: {secret_width}x{secret_height}")
            print(f"Header used {header_pixels_used} pixels")

            # Calculate starting position for image data (skip header area)
            start_y = (header_pixels_used // width) + 1
            start_x = 0

            # Create new image for extracted data
            extracted_img = Image.new("RGB", (secret_width, secret_height))
            extracted_pixels = extracted_img.load()

            # Extract hidden image pixels (using 4 LSBs) from offset position
            for sy in range(secret_height):
                for sx in range(secret_width):
                    # Calculate position in stego image (offset by header size)
                    cx = sx + start_x
                    cy = sy + start_y

                    if cx < width and cy < height:
                        stego_pixel = pixels[cx, cy]

                        # Extract 4 LSBs and shift to MSBs, then fill lower bits
                        extracted_pixel = []
                        for channel in range(3):
                            # Get 4 LSBs and shift them to MSBs
                            hidden_bits = (stego_pixel[channel] & 0x0F) << 4
                            # Duplicate the 4 bits to fill the lower 4 bits for better quality
                            hidden_bits = hidden_bits | ((stego_pixel[channel] & 0x0F))
                            extracted_pixel.append(hidden_bits)

                        extracted_pixels[sx, sy] = tuple(extracted_pixel)

            # Save the extracted image
            extracted_img.save(output_path)
            print(f"Image extracted successfully to: {output_path}")
            return True

        except Exception as e:
            import traceback

            print(f"Error extracting image: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def hide_file_in_image(cover_image_path, secret_file_path, output_path):
        """
        Hide any file (as binary data) in an image

        Args:
            cover_image_path: Path to the cover image
            secret_file_path: Path to the file to hide
            output_path: Path to save the stego image

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read the secret file as binary
            with open(secret_file_path, "rb") as f:
                secret_data = f.read()

            # Get file extension
            file_ext = os.path.splitext(secret_file_path)[1]

            # Create header with file size and extension
            header = f"{len(secret_data)}:{file_ext}<<HEADER>>"

            # Combine header and data
            full_data = header.encode() + secret_data + b"<<END>>"

            # Convert to binary
            binary_data = Steganography._string_to_binary(full_data)

            # Open the cover image
            img = Image.open(cover_image_path).convert("RGB")
            width, height = img.size

            # Check capacity
            max_bytes = width * height * 3
            if len(binary_data) > max_bytes:
                raise ValueError(
                    f"Image too small. Need {len(binary_data)} bits, have {max_bytes}"
                )

            # Hide data
            pixels = img.load()
            data_index = 0

            for y in range(height):
                for x in range(width):
                    if data_index < len(binary_data):
                        pixel = list(pixels[x, y])
                        for channel in range(3):
                            if data_index < len(binary_data):
                                pixel[channel] = pixel[channel] & ~1 | int(
                                    binary_data[data_index]
                                )
                                data_index += 1
                        pixels[x, y] = tuple(pixel)
                    else:
                        break
                if data_index >= len(binary_data):
                    break

            img.save(output_path)
            return True

        except Exception as e:
            print(f"Error hiding file: {e}")
            return False

    @staticmethod
    def extract_file_from_image(stego_image_path, output_directory):
        """
        Extract hidden file from a stego image

        Args:
            stego_image_path: Path to the stego image
            output_directory: Directory to save the extracted file

        Returns:
            Path to extracted file or None if error
        """
        try:
            # Open the stego image
            img = Image.open(stego_image_path).convert("RGB")
            width, height = img.size
            pixels = img.load()

            # Extract binary data
            binary_data = ""
            for y in range(height):
                for x in range(width):
                    pixel = pixels[x, y]
                    for channel in range(3):
                        binary_data += str(pixel[channel] & 1)

            # Convert to bytes
            byte_data = bytearray()
            for i in range(0, len(binary_data), 8):
                byte = binary_data[i : i + 8]
                if len(byte) == 8:
                    byte_data.append(int(byte, 2))

            # Find header
            header_end = byte_data.find(b"<<HEADER>>")
            if header_end == -1:
                raise ValueError("No valid header found")

            header = byte_data[:header_end].decode()
            file_size, file_ext = header.split(":")
            file_size = int(file_size)

            # Extract file data
            data_start = header_end + len(b"<<HEADER>>")
            file_data = byte_data[data_start : data_start + file_size]

            # Save extracted file
            output_path = os.path.join(output_directory, f"extracted{file_ext}")
            with open(output_path, "wb") as f:
                f.write(file_data)

            return output_path

        except Exception as e:
            print(f"Error extracting file: {e}")
            return None
