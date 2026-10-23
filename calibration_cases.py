# Added after the first simulation run to calibrate the review rule

CALIBRATION_CLEAR = (
    # Cardiology
    ("Patient reports a dull ache in the chest that increases during light walking", "cardiology"),
    ("Elderly male with a history of atrial fibrillation presenting with irregular heartbeat", "cardiology"),
    # Neurology
    ("Adult with sudden numbness in the left hand and slight facial drooping", "neurology"),
    ("Patient experiencing recurrent migraines with visual auras and light sensitivity", "neurology"),
    # Pediatrics
    ("Three year old with a barking cough and inspiratory stridor", "pediatrics"),
    ("Infant with persistent diaper rash and low-grade fever", "pediatrics"),
    # OBGYN
    ("Pregnant patient at 34 weeks with regular contractions every five minutes", "obstetrics and gynecology"),
    ("Post-menopausal woman with irregular vaginal bleeding", "obstetrics and gynecology"),
    # Orthopedics
    ("Patient with a suspected ankle sprain after twisting it on a curb", "orthopedics"),
    ("Chronic knee pain in a 60 year old with stiffness upon waking", "orthopedics"),
    # Gastroenterology
    ("Adult with persistent heartburn and a sour taste in the mouth", "gastroenterology"),
    ("Patient with clay-colored stools and yellowing of the skin", "gastroenterology"),
    # General Medicine
    ("Patient with a persistent low-grade fever and generalized fatigue for two weeks", "general medicine"),
    ("Adult with a skin rash and itchy eyes following a new detergent use", "general medicine"),

    # length control
    ("Patient reports a history of chronic lower back pain that worsens with sitting. They describe a sharp sensation radiating down the left leg to the ankle, primarily after long periods of inactivity.", "orthopedics"),
    ("Adult female presents with persistent abdominal bloating and discomfort. She reports a gradual increase in flatulence and irregular bowel movements over the last six months, unresponsive to diet changes.", "gastroenterology"),
    ("Older male with recurring bouts of sudden dizziness and momentary loss of balance. He describes a sensation of the room spinning, accompanied by occasional ringing in the ears.", "neurology"),
    ("Patient presents with a prolonged, non-productive cough and shortness of breath during exertion. They have a history of seasonal allergies and describe a tightening sensation in the chest.", "cardiology"),
)

MIXED_CASES = (
    ("Patient has a mild headache and some nausea, but also mentions occasional fluttering in the chest and slight dizziness when standing up", "mixed"),
    ("Older adult with sudden shortness of breath, mild confusion, and severe abdominal cramping", "mixed"),
    ("Adult with mild chest tightness, recurring headaches, and heartburn after eating", "mixed"),
    ("Adult presenting with high fever, slurred speech, and lower extremity edema", "mixed"),
    ("Patient reports intermittent knee pain, a persistent dry cough, and occasional stomach cramps after meals", "mixed"),
    ("Patient with severe lower back pain, dizziness, and a history of recurrent nausea", "mixed"),
)
