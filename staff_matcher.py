"""
Staff Profile & Visual Identification Module
Recognizes store staff (such as the female front desk staff) by:
1. Color histogram correlation with reference profiles in data/staff_profiles/
2. Clothing signature (white top + blue denim jeans)
3. Stationary dwell / counter position
"""
import os
import cv2
import numpy as np
import logging

logger = logging.getLogger("staff_matcher")

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "data", "staff_profiles")

class StaffMatcher:
    def __init__(self):
        self.ref_histograms = []
        self._load_reference_profiles()

    def _load_reference_profiles(self):
        self.ref_histograms = []
        if not os.path.exists(PROFILES_DIR):
            return
        for fname in os.listdir(PROFILES_DIR):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                fpath = os.path.join(PROFILES_DIR, fname)
                img = cv2.imread(fpath)
                if img is not None:
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                    hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
                    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
                    self.ref_histograms.append((fname, hist))
        logger.info(f"Loaded {len(self.ref_histograms)} staff reference profiles.")

    def match_person_crop(self, person_bgr: np.ndarray, cx: float = 0.5, cy: float = 0.5) -> dict:
        """
        Evaluates whether a cropped person image matches the staff profile.
        Returns:
            {
                "is_staff": bool,
                "confidence": float,
                "reason": str
            }
        """
        if person_bgr is None or person_bgr.shape[0] < 30 or person_bgr.shape[1] < 15:
            return {"is_staff": False, "confidence": 0.0, "reason": "Crop too small"}

        h, w = person_bgr.shape[:2]

        # 1. Clothing signature check (White top + Blue denim lower)
        upper = person_bgr[int(h * 0.10):int(h * 0.50), :]
        lower = person_bgr[int(h * 0.45):int(h * 0.90), :]

        white_ratio = 0.0
        if upper.size > 0:
            hsv_u = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
            white_mask = cv2.inRange(hsv_u, np.array([0, 0, 150]), np.array([180, 70, 255]))
            white_ratio = float(np.mean(white_mask > 0))

        blue_ratio = 0.0
        if lower.size > 0:
            hsv_l = cv2.cvtColor(lower, cv2.COLOR_BGR2HSV)
            blue_mask = cv2.inRange(hsv_l, np.array([90, 30, 30]), np.array([140, 255, 255]))
            blue_ratio = float(np.mean(blue_mask > 0))

        clothing_score = 0.0
        if white_ratio >= 0.22 and blue_ratio >= 0.20:
            clothing_score = min(1.0, (white_ratio + blue_ratio) * 1.2)

        # 2. Histogram correlation with loaded staff profiles
        best_hist_score = 0.0
        if self.ref_histograms:
            hsv_crop = cv2.cvtColor(person_bgr, cv2.COLOR_BGR2HSV)
            hist_crop = cv2.calcHist([hsv_crop], [0, 1], None, [50, 60], [0, 180, 0, 256])
            cv2.normalize(hist_crop, hist_crop, 0, 1, cv2.NORM_MINMAX)

            for name, ref_hist in self.ref_histograms:
                score = cv2.compareHist(ref_hist, hist_crop, cv2.HISTCMP_CORREL)
                if score > best_hist_score:
                    best_hist_score = score

        # 3. Overall confidence calculation
        # If clothing matches strongly (white top + denim) and histogram resembles staff
        combined_conf = (best_hist_score * 0.55) + (clothing_score * 0.45)
        
        # Also flag if clearly matching clothing pattern (white top + denim)
        if clothing_score > 0.65 or best_hist_score > 0.68 or combined_conf > 0.58:
            return {
                "is_staff": True,
                "confidence": round(float(combined_conf), 2),
                "reason": f"Visual match: Hist={best_hist_score:.2f}, Clothes={clothing_score:.2f} (White: {white_ratio:.2f}, Denim: {blue_ratio:.2f})"
            }

        return {
            "is_staff": False,
            "confidence": round(float(combined_conf), 2),
            "reason": f"Customer pattern: Hist={best_hist_score:.2f}, Clothes={clothing_score:.2f}"
        }

# Global singleton
staff_matcher = StaffMatcher()
