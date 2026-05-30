# head pose + eye gaze using mediapipe and opencv

import cv2 # reads webcam frames and displays the output
from typing import TYPE_CHECKING

# Allow static analyzers/type checkers to see the mediapipe import while
# keeping a runtime-friendly fallback if mediapipe isn't installed.
if TYPE_CHECKING:
    import mediapipe as mp  # type: ignore
else:
    try:
        import mediapipe as mp  # detects 468 face landmarks and 21 hand landmarks
    except Exception:  # pragma: no cover - allow linting when mediapipe isn't installed
        mp = None
    # At runtime, if mediapipe is missing the caller will get a clear error.
    # This avoids import-time linter/IDE errors in environments without mediapipe.
import numpy as np # allows you to do math with the face and hand landmarks 
import math # allows you to do math with the face and hand landmarks

# ––––––––– setup Mediapipe Face Mesh and Hands –––––––––

mp_face_mesh = mp.solutions.face_mesh # loads the face mesh from mediapipe

face_mesh = mp_face_mesh.FaceMesh (
    max_num_faces = 1, # only tracks 1 face (you)
    refine_landmarks = True, # also detects iris landmarks (for eye gaze tracking)
    min_detection_confidence = 0.5, # how confident mediapipe should be to detect a face
    min_tracking_confidence = 0.5 # how confident it must be to keep tracking frame to frame
)

# ––––––––– 3D head pose constraints –––––––––
# these are the real world 3D coordinates in mm of the 6 face landmarks that we will use to estimate the head pose
# we compare thses to where they appear on screen to calculate the head tilt angle

MODEL_POINTS = np.array ([
    (0.0, 0.0, 0.0),             # nose tip
    (0.0, -330.0, -65.0),        # chin bottom
    (-225.0, 170.0, -135.0),     # left eye left corner
    (225.0, 170.0, -135.0),      # right eye right corner
    (-150.0, -150.0, -125.0),   # left mouth corner
    (150.0, -150.0, -125.0)     # right mouth corner
], dtype=np.float64)

# these are the mediapipe landmark index numbers for those 6 points
# mediapipe gives 468 numbers from where we pick these 6

LANDMARK_IDS = [1, 152, 263, 33, 287, 57] 
# nose tip, chin bottom, left eye left corner, right eye right corner, left mouth corner, right mouth corner

# ––––––––– 3D distance between 2 landmarks –––––––––
def dist3d (a, b):
    return math.sqrt ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)

# ––––––––– head pitch calculation –––––––––
# 'pitch' = up/down head tilt angle in degrees
# positive pitch means looking down, negative pitch means looking up
# near zero 'pitch' means head-straight

def get_head_pitch (landmarks, img_w, img_h):
    # convert the 6 landmarks from normalised (0, 1) coordinates to pixel coordinates
    image_points = np.array ([
        (landmarks[i].x * img_w, landmarks[i].y * img_h)
        for i in LANDMARK_IDS
    ], dtype=np.float64)

    focal_length = img_w # approximate focal length in pixels (usually the width of the image) frame length
    center = (img_w / 2, img_h / 2) # optical centre = middle of the frame

    # camera matrix describes how the lens maps 3D world to 2D image
    camera_matrix = np.array ([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    dist_coeffs = np.zeros((4, 1)) # assume no lens distortion and shape = (4 rows, 1 column)

    #solvePnP : given 3D model points, their corresponding 2D image points
    # calculate the rotation and translation of the head in 3D space

    success, rotation_vec, _ = cv2.solvePnP (
        MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE # It- starts with an estimated pose, repeatedly improves it, minimizes reprojection error
    )
    if not success:
        return 0.0 # returns 0 if calculation fails for some reason
    
    rot_mat, _ = cv2.Rodrigues (rotation_vec) # converts rotation vector to rotation matrix (3x3)
    pitch = math.degrees(math.asin(-rot_mat[2][1])) # extract pitch angle in degrees
    return pitch

# ––––––––– eye gaze detection –––––––––
# it checks where iris is positioned inside the eye opening
# if the iris is looking down = at phone

def eye_looking_down (landmarks):
    try:
        results = []
        # check both eyes (top_eyelid, bottom_eyelid, iris_center) landmark IDs
        for top_idx, bottom_idx, iris_idx in [(159, 145, 468), (386, 374, 473)]:
            top = landmarks[top_idx] # top eyelid landmark
            bottom = landmarks[bottom_idx] # bottom eyelid landmark
            iris = landmarks[iris_idx] # iris (pupil) center landmark

            eye_h = dist3d (top, bottom) # height of eye opening in 3d
            if eye_h < 0.005: # eye is basically closed
                return None 
            
            # iris_rel : 0.0 = iris at very top of eye, 1.0 = iris at very bottom of eye
            iris_rel = (iris.y - top.y) / (bottom.y - top.y + 1e-6)
            results.append(iris_rel)
        
        avg = sum(results) / len(results) # average for both eyes
        return avg > 0.52, avg # returns (is looking down, raw value)
    except:
        return None # if calculation fails for some reason, return None (not looking down)
    
# ––––––––– main detection function –––––––––
def analyze_frame (frame_bytes):
    """
    Input : raw JPEG bytes from browser webcam
    Output : dict with status and debug info
    """

    # decode JPEG bytes into a NumPy image array
    np_arr = np.frombuffer (frame_bytes, np.uint8) # convert bytes to 1D array of uint8
    frame = cv2.imdecode (np_arr, cv2.IMREAD_COLOR) # decode JPEG to color image (BGR format)

    if frame is None:
        return {'status': 'no_frame', 'alarm': False}
    
    img_h, img_w = frame.shape[:2] # get image dimensions

    # convert BGR (opencv default) to RGB (mediapipe requirement)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb) # run mediapipe face detection

    # No Face Detected
    if not results.multi_face_landmarks:
        return {'status': 'no_face', 'alarm': False, 'pitch': 0, 'iris': 0}
    
    # Face Found - Extract landmarks
    lms = results.multi_face_landmarks[0].landmark # get list of 468 face landmarks for the first detected face
    pitch = get_head_pitch (lms, img_w, img_h) # calculate head tilt
    eye_result = eye_looking_down (lms) # check eye gaze

    if eye_result is None:
        return {'status': 'eyes_closed', 'alarm': False, 'pitch': round(pitch, 1), 'iris': 0}
    
    is_looking_down, iris_val = eye_result

    # 'Head straight' = pitch between -10 degree and +20 degree (normal monitor viewing range)
    head_straight = -10 < pitch < 20

    # 'Eyes centered' = iris not looking too far down
    eyes_centered = 0.20 < iris_val < 0.68

    # Looking at screen = head is straight AND eyes are not looking down
    looking_at_screen = head_straight and eyes_centered

    # ALARM triggers when NOT looking at screen = looking at phone
    alarm = not looking_at_screen

    return {
        'status' : 'ok',
        'alarm' : alarm,
        'looking_at_screen' : looking_at_screen,
        'pitch' : round(pitch, 1),
        'iris' : round(iris_val, 3),
        'head_straight' : head_straight,
        'eyes_centered' : eyes_centered
    }