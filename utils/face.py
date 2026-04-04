import cv2
import numpy as np
from PIL import Image
import io
import gc
import os
import insightface
from insightface.app import FaceAnalysis

# Globally initialize precisely on container boot natively avoiding loop memory leaks.
# 'buffalo_sc' is incredibly tiny (~15MB) and executes seamlessly on strict CPU execution limits.
try:
    face_app = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider'])
    face_app.prepare(ctx_id=0, det_size=(640, 640))
except Exception as e:
    print(f"CRITICAL MODEL STARTUP ERROR: {e}")
    face_app = None

def check_system_resources(max_ram_percent=85.0, max_cpu_load=75.0):
    """
    Evaluates hardware thresholds explicitly natively without relying on psutil 
    to preserve dependencies strictly mapping unbouncable CPU servers.
    """
    try:
        # Check Linux memory profile securely
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        mem_info = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                mem_info[parts[0].strip(':')] = int(parts[1])
                
        total_mem = mem_info.get('MemTotal', 1)
        free_mem = mem_info.get('MemAvailable', mem_info.get('MemFree', 0))
        used_mem_percent = ((total_mem - free_mem) / total_mem) * 100.0

        if used_mem_percent > max_ram_percent:
            return False, f"Server memory constrained ({used_mem_percent:.1f}% used)."

        # Check CPU Linux load average over 1 min
        # Load average defines threads waiting. On a 1 CPU system, load > 0.75 means roughly 75% load constraints.
        load1, load5, load15 = os.getloadavg()
        cpu_load_percent = load1 * 100.0

        if cpu_load_percent > max_cpu_load:
             return False, f"Server CPU constrained (Load: {cpu_load_percent:.1f}%)."

        return True, "OK"
    except Exception as e:
        # Bypass on Non-Linux local testing
        return True, "Check bypassed (Non-Linux OS)"

def get_image_tensor(image_bytes, max_dim=640):
    """ Fast streaming constraint algorithm bypassing buffer bloat. """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(image)
        # BGR conversion aligning with exact insightface matrices
        img_cv2 = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # Scaling limits down strictly saving massive byte allocations
        h, w = img_cv2.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img_cv2 = cv2.resize(img_cv2, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        del image
        del img_np
        gc.collect()
        return img_cv2
    except Exception as e:
        print(f"Tensor extraction failed: {e}")
        return None

def extract_face_encodings(image_bytes):
    """ Extract single or max array face vectors safely coercing formats to float32 mitigating Database sizing blobs. """
    if not face_app: return []
    
    ok, msg = check_system_resources()
    if not ok:
        print(f"Skipping ML inference forcefully: {msg}")
        return []

    try:
        img_tensor = get_image_tensor(image_bytes)
        if img_tensor is None: return []

        faces = face_app.get(img_tensor)
        
        del img_tensor
        gc.collect()

        # Extract only the 512D norm embeddings safely coercing single precision array lists
        return [face.normed_embedding.astype(np.float32).tolist() for face in faces]
        
    except Exception as e:
        print(f"Failed embedding extraction gracefully, bypassing 500 crashes: {e}")
        return []

def match_faces_in_group(group_image_bytes, known_encodings_dict, tolerance=1.0):
    """ Uses numpy distancing explicitly matching matrices smoothly bypassing heavy loops. """
    if not face_app: return []

    ok, msg = check_system_resources()
    if not ok:
        print(f"Skipping group inference forcefully: {msg}")
        return []

    try:
        img_tensor = get_image_tensor(group_image_bytes)
        if img_tensor is None: return []

        faces = face_app.get(img_tensor)
        del img_tensor
        gc.collect()

        identified_rolls = set()
        
        for unknown_face in faces:
            u_enc = unknown_face.normed_embedding.astype(np.float32)
            
            best_roll = None
            min_dist = float('inf')

            for roll_no, saved_encs in known_encodings_dict.items():
                if not saved_encs: continue
                
                # Natively array distance Euclidean comparisons utilizing optimized C implementations within NumPy
                for s_enc in saved_encs:
                    s_enc_np = np.array(s_enc, dtype=np.float32)
                    dist = np.linalg.norm(u_enc - s_enc_np)
                    
                    if dist < tolerance and dist < min_dist:
                        min_dist = dist
                        best_roll = roll_no
                        
            if best_roll:
                identified_rolls.add(best_roll)

        return list(identified_rolls)
    except Exception as e:
        print(f"Group matching crashed explicitly recovering cleanly maintaining up-time: {e}")
        return []
