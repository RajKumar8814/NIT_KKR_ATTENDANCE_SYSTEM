import cv2
import face_recognition
import numpy as np
from PIL import Image
import io
import gc

def resize_image_for_memory(image_bytes, max_width=600):
    """
    Resizes image from raw bytes if its width exceeds max_width.
    Returns RGB numpy array suitable for face_recognition.
    Vital for Render's 512MB RAM constraint.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB (in case of RGBA or Grayscale)
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        width, height = image.size
        # Resize if width is larger than max limit
        if width > max_width:
            ratio = max_width / float(width)
            new_height = int(float(height) * ratio)
            image = image.resize((max_width, new_height), Image.LANCZOS)
        
        # Convert to numpy array
        img_array = np.array(image)
        # Release PIL image memory
        del image
        return img_array
    except Exception as e:
        print(f"Image resize error: {e}")
        return None

def extract_face_encodings(image_bytes):
    """
    Given image bytes, parse it, resize it to save memory,
    and convert to face encodings.
    """
    img_array = resize_image_for_memory(image_bytes)
    if img_array is None:
        return []

    # Find face locations first to pass them into encodings
    # This might use memory so be careful
    locations = face_recognition.face_locations(img_array, model="hog")
    encodings = face_recognition.face_encodings(img_array, locations)
    
    # Trigger garbage collection aggressively
    del img_array
    gc.collect()
    
    return [enc.tolist() for enc in encodings]

def match_faces_in_group(group_image_bytes, known_encodings_dict, tolerance=0.53):
    """
    Detect faces in a group photo and match against the complete DB encodings.
    `known_encodings_dict` is { 'roll_no': [enc1, enc2, ...], ... }
    Returns a list of identified roll_nos.
    """
    img_array = resize_image_for_memory(group_image_bytes)
    if img_array is None:
        return []

    group_locations = face_recognition.face_locations(img_array, model="hog")
    group_encodings = face_recognition.face_encodings(img_array, group_locations)
    
    del img_array
    gc.collect()

    identified_roll_nos = set()
    
    for unknown_encoding in group_encodings:
        best_match_roll_no = None
        min_distance = float('inf')
        
        for roll_no, saved_encodings in known_encodings_dict.items():
            if not saved_encodings:
                continue
                
            match_results = face_recognition.compare_faces(saved_encodings, unknown_encoding, tolerance=tolerance)
            face_distances = face_recognition.face_distance(saved_encodings, unknown_encoding)
            
            # Find best match in this student's encodings
            if any(match_results):
                best_match_index = np.argmin(face_distances)
                if face_distances[best_match_index] < min_distance:
                    min_distance = face_distances[best_match_index]
                    best_match_roll_no = roll_no
                    
        if best_match_roll_no:
            identified_roll_nos.add(best_match_roll_no)
            
    # Free local references
    del group_encodings
    gc.collect()
    
    return list(identified_roll_nos)
