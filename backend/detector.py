import cv2
import numpy as np
import math

# Old MediaPipe API — works on Render's free Linux server (no GPU needed)
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh


# 3D real-world face coordinates in mm — used for head pose calculation
MODEL_POINTS = np.array([
    (0.0,    0.0,    0.0),       # nose tip
    (0.0,  -330.0, -65.0),       # chin
    (-225.0, 170.0, -135.0),     # left eye corner
    (225.0,  170.0, -135.0),     # right eye corner
    (-150.0, -150.0, -125.0),    # left mouth corner
    (150.0,  -150.0, -125.0)     # right mouth corner
], dtype=np.float64)

LANDMARK_IDS = [1, 152, 33, 263, 61, 291]

def dist3d(a, b):
    return math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2)

def get_head_pitch(landmarks, img_w, img_h):
    image_points = np.array([
        (landmarks[i].x * img_w, landmarks[i].y * img_h)
        for i in LANDMARK_IDS
    ], dtype=np.float64)

    focal_length = img_w
    center = (img_w/2, img_h/2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    dist_coeffs = np.zeros((4,1))
    success, rotation_vec, _ = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not success:
        return 0.0

    rot_mat, _ = cv2.Rodrigues(rotation_vec)
    pitch = math.degrees(math.asin(-rot_mat[2][1]))
    return pitch

def eye_looking_down(landmarks):
    try:
        results = []
        for top_idx, bottom_idx, iris_idx in [(159, 145, 468), (386, 374, 473)]:
            top    = landmarks[top_idx]
            bottom = landmarks[bottom_idx]
            iris   = landmarks[iris_idx]
            eye_h  = dist3d(top, bottom)
            if eye_h < 0.005:
                return None
            iris_rel = (iris.y - top.y) / (bottom.y - top.y + 1e-6)
            results.append(iris_rel)
        avg = sum(results) / len(results)
        return avg > 0.52, avg
    except:
        return None

def analyze_frame(frame_bytes):
    np_arr = np.frombuffer(frame_bytes, np.uint8)
    frame  = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return {'status': 'no_frame', 'alarm': False}
    
    # Create fresh face_mesh per request — fixes timestamp mismatch on server
    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:
    
        img_h, img_w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Use old solutions API — no graphics library needed
        results = face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return {'status': 'no_face', 'alarm': False, 'pitch': 0, 'iris': 0}

        lms   = results.multi_face_landmarks[0].landmark
        pitch = get_head_pitch(lms, img_w, img_h)
        eye_result = eye_looking_down(lms)

        if eye_result is None:
            return {'status': 'eyes_closed', 'alarm': False, 'pitch': round(pitch,1), 'iris': 0}

        is_looking_down, iris_val = eye_result
        head_straight     = -10 < pitch < 20
        eyes_centered     = 0.20 < iris_val < 0.68
        looking_at_screen = head_straight and eyes_centered
        alarm             = not looking_at_screen

        return {
            'status':            'ok',
            'alarm':             alarm,
            'looking_at_screen': looking_at_screen,
            'pitch':             round(pitch, 1),
            'iris':              round(iris_val, 3),
            'head_straight':     head_straight,
            'eyes_centered':     eyes_centered
        }