def get_bjj_analysis_prompt(user_desc, user_belt, opp_desc, opp_belt, max_duration_sec=90):
    """
    Generates a highly constrained, anti-hallucination prompt for BJJ video analysis
    with strict visual identity tracking.
    """
    return f"""
    You are an elite BJJ tactical analyst evaluating a video of maximum {max_duration_sec} seconds.
    
    =========================================================
    IDENTITY TRACKING (CRITICAL - READ CAREFULLY):
    =========================================================
    - USER VISUAL ANCHOR: {user_desc} (Belt: {user_belt})
    - OPPONENT VISUAL ANCHOR: {opp_desc} (Belt: {opp_belt})
    
    WARNING: In BJJ, athletes constantly roll, scramble, and swap top/bottom positions. 
    1. NEVER identify athletes by their spatial position (e.g., do not assume "User" is always on top).
    2. YOU MUST identify athletes STRICTLY by their visual clothing and physical traits (e.g., jersey color, gi color, hair).
    3. If the {user_desc} starts on top, gets swept, and ends up on bottom, THEY ARE STILL THE USER. Do not swap their identities in your analysis!

    =========================================================
    STRICT ANTI-HALLUCINATION RULES:
    =========================================================
    - ZERO HALLUCINATION: Do not fabricate submissions, transitions, or outcomes that did not occur visually. If an event is ambiguous, describe the motion, not a specific technique name.
    - 5-SECOND INTERVALS: You MUST break down the ENTIRE video in exactly 5-second intervals (0:00-0:05, 0:05-0:10, etc.).
    - EXACT COUNTS: Provide EXACTLY 3 strengths and 3 weaknesses for the USER, and EXACTLY 3 strengths and 3 weaknesses for the OPPONENT.
    - TIMESTAMPS: Tie all strengths, weaknesses, opportunities, and key moments to exact timestamps.

    Provide a JSON response strictly matching this schema:
    {{
        "overall_score": 75,
        "performance_label": "SOLID PERFORMANCE",
        "grades": {{"defense": "C+", "offense": "C", "control": "C"}},
        "user_stats": {{"offense": 66, "defense": 70, "guard": 64, "passing": 62, "standup": 50}},
        "opponent_stats": {{"offense": 60, "defense": 65, "guard": 60, "passing": 55, "standup": 50}},
        "interval_breakdown": [
            {{"time": "0:00-0:05", "breakdown": "Strictly what happened based on visual evidence..."}}
        ],
        "user_strengths": ["(MM:SS) detail", "(MM:SS) detail", "(MM:SS) detail"],
        "user_weaknesses": ["(MM:SS) detail", "(MM:SS) detail", "(MM:SS) detail"],
        "opponent_strengths": ["(MM:SS) detail", "(MM:SS) detail", "(MM:SS) detail"],
        "opponent_weaknesses": ["(MM:SS) detail", "(MM:SS) detail", "(MM:SS) detail"],
        "missed_opportunities": [{{"time": "MM:SS", "category": "POSITION", "title": "...", "description": "..."}}],
        "key_moments": [{{"time": "MM:SS", "title": "...", "description": "..."}}],
        "coach_notes": "Direct, evidence-anchored feedback based strictly on the detected intervals."
    }}
    """