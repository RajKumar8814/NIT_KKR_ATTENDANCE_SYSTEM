import cv2
import numpy as np
from PIL import Image
import io
import gc
import os
import insightface
from insightface.app import FaceAnalysis

# Global pre-initialization specifically designed for 1 CPU / 1GB RAM Railway Environment.
# Using 'buffalo_sc' ensures we stay well under 800MB Docker image size.
try:
    # Synchronous pre-load of the model at application startup to avoid first-request timeout
    # ctx_id=0 means CPU-only mode
    face_app = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider'])
    face_app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.4)
except Exception as e:
    print(f"CRITICAL: Failed to load InsightFace Model on boot: {e}")
    face_app = None

def check_ram_usage(max_percent=90.0):
    """
    Safely checks Linux memory profile to prevent OOM (Out Of Memory) crashes.
    """
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        mem_info = {line.split(':')[0]: int(line.split(':')[1].split()[0]) for line in lines}
        total = mem_info.get('MemTotal', 1)
        free = mem_info.get('MemAvailable', mem_info.get('MemFree', 0))
        used_p = ((total - free) / total) * 100.0
        return used_p < max_percent, used_p
    except:
        # Non-linux environment check bypass
        return True, 0.0

def get_optimized_tensor(image_bytes, target_dim=1600):
    """
    Resizes image bytes to an optimized tensor format using OpenCV-direct decoding.
    Crucial for handling various JPEG metadata formats that PIL sometimes skips.
    High resolution (1600px) allows for detecting faces in the 4th/5th rows.
    """
    try:
        # Direct decode from memory buffer to OpenCV BGR format (fastest)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_cv2 = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_cv2 is None:
            return None, "OpenCV failed to decode image bytes."

        # Scale protection: Downscale large photos to 1600px to ensure CPU-bound speed
        h, w = img_cv2.shape[:2]
        if max(h, w) > target_dim:
            scale = target_dim / max(h, w)
            img_cv2 = cv2.resize(img_cv2, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        return img_cv2, None
    except Exception as e:
        return None, str(e)

def extract_face_encodings(image_bytes):
    """
    Extracts face vectors (embeddings) from raw image bytes.
    Returns list of 512D vectors as Python lists. 
    """
    if not face_app: return []
    
    # RAM Protection circuit
    ok, ram_p = check_ram_usage()
    if not ok:
        print(f"ABORT: Memory usage too high ({ram_p:.1f}%) to process Face ML.")
        return []

    try:
        img_tensor, err = get_optimized_tensor(image_bytes, target_dim=640) # Enrollment uses smaller dim for speed
        if img_tensor is None: 
            print(f"ERROR: {err}")
            return []

        # Run Face Discovery + Recognition
        faces = face_app.get(img_tensor)
        print(f"DEBUG: Found {len(faces)} faces in enrollment photo.")
        
        del img_tensor
        gc.collect()

        # We strictly use normed_embedding for stable Euclidean distance matching
        return [face.normed_embedding.astype(np.float32).tolist() for face in faces]
        
    except Exception as e:
        print(f"Encoding extraction error: {e}")
        return []

def match_faces_in_group(group_image_bytes, known_encodings_dict, tolerance=1.0):
    """
    Matches faces in a group photo against the database list of encodings.
    Now updated for Adaptive High-Density Scanning (1600px, 0.4 Thresh).
    Returns (list_of_rolls, error_message)
    """
    if not face_app: 
        return [], "AI Engine not initialized correctly on boot."

    # CPU/RAM Check
    ok, ram_p = check_ram_usage()
    if not ok: 
        return [], f"Memory Limit (RAM: {ram_p:.1f}%) is too high to run AI scanning safely."

    try:
        # Increase scan resolution for back-row faces (target_dim=1600)
        img_tensor, err = get_optimized_tensor(group_image_bytes, target_dim=1600)
        if img_tensor is None: 
            return [], f"Photo Decode Error: {err}"

        # Lower det_thresh to 0.4 for improved scanning of back rows and occlusions
        # Wrapped in extra try to catch specific AI core timeouts
        try:
            faces = face_app.get(img_tensor)
        except Exception as ai_err:
            return [], f"AI Detection Failed: {ai_err}. (Tip: Try a smaller photo)"

        print(f"DEBUG: Scanned {len(faces)} faces at high density.")
        
        del img_tensor
        gc.collect()

        identified_rolls = set()
        
        for unknown_face in faces:
            u_enc = unknown_face.normed_embedding.astype(np.float32)
            
            best_match_roll = None
            min_dist = float('inf')

            for roll_no, student_encodings in known_encodings_dict.items():
                if not student_encodings: continue
                
                for s_enc in student_encodings:
                    try:
                        s_enc_np = np.array(s_enc, dtype=np.float32)
                        
                        # Shape Safety Check: buffalo_sc uses 128D, legacy models used 512D
                        if u_enc.shape != s_enc_np.shape:
                            continue

                        # Euclidean distance for normalized vectors
                        dist = np.linalg.norm(u_enc - s_enc_np)
                        
                        if dist < tolerance and dist < min_dist:
                            min_dist = dist
                            best_match_roll = roll_no
                    except:
                        continue
                        
            if best_match_roll:
                identified_rolls.add(best_match_roll)

        print(f"DEBUG: Identified {len(identified_rolls)} students matches.")
        return list(identified_rolls), None

    except Exception as general_err:
        return [], f"System Overhead Warning: {general_err}"
