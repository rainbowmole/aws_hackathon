"""Run a rural triage routing simulation against the local Decider."""

from __future__ import annotations

import math
import statistics
import time

from decider_patterns.specialty_policy_decider import SpecialtyPolicyDecider


# Original 6 cases - relabeled after redesign to exclude 'emergency medicine' from choices
ORIGINAL_CASES = (
    (
        "patient has crushing central chest pain, sweating, and shortness of "
        "breath for 20 minutes",
        "cardiology",
    ),
    ("7 year old with fever, wheezing, and poor oral intake since yesterday", "pediatrics"),
    ("older adult with sudden facial droop and difficulty speaking", "neurology"),
    (
        "pregnant patient at 34 weeks with severe headache and high blood pressure",
        "obstetrics and gynecology",
    ),
    ("adult with persistent palpitations and dizziness after exertion", "cardiology"),
    ("patient with cough and fatigue but stable vital signs for five days", "general medicine"),
)

# 20+ New Labeled Notes (Holdout Set)
NEW_CASES = (
    # Cardiology
    ("Patient reports intermittent chest tightness and left arm numbness during exercise", "cardiology"),
    ("Older adult with sudden onset of severe palpitations and fainting spell", "cardiology"),
    ("Chronic heart failure patient with sudden increase in edema and shortness of breath", "cardiology"),
    # Neurology
    ("Sudden loss of vision in right eye and severe vertigo", "neurology"),
    ("Patient with progressive muscle weakness and difficulty swallowing over 2 weeks", "neurology"),
    ("Severe thunderclap headache unlike any other, followed by vomiting", "neurology"),
    # Pediatrics
    ("Toddler with high fever, rash, and refusal to walk", "pediatrics"),
    ("Infant with persistent vomiting and signs of dehydration", "pediatrics"),
    ("School-age child with sudden onset of sore throat and high fever", "pediatrics"),
    # OBGYN
    ("Pregnant woman at 20 weeks with sudden vaginal bleeding", "obstetrics and gynecology"),
    ("Post-partum patient with sudden shortness of breath and chest pain", "obstetrics and gynecology"),
    ("Woman in third trimester with severe swelling of legs and face", "obstetrics and gynecology"),
    # Orthopedics
    ("Patient with obvious open fracture of the tibia after a machinery accident", "orthopedics"),
    ("Severe joint pain and redness in the knee with restricted movement", "orthopedics"),
    ("Elderly patient with hip pain and inability to bear weight after a fall", "orthopedics"),
    # Gastroenterology
    ("Acute onset of severe right upper quadrant pain radiating to the shoulder", "gastroenterology"),
    ("Patient with hematemesis and history of chronic liver disease", "gastroenterology"),
    ("Severe abdominal cramping and bloody stools for 24 hours", "gastroenterology"),
    # General Medicine
    ("Adult with persistent low-grade fever, joint pain, and night sweats", "general medicine"),
    ("Patient with chronic cough, weight loss, and history of smoking", "general medicine"),
    ("Mild abdominal discomfort and nausea associated with known diabetes", "general medicine"),
)

def run_set(name: str, cases: tuple, decider: SpecialtyPolicyDecider) -> float:
    latencies: list[float] = []
    correct = 0
    print(f"\n--- Testing Set: {name} ---")

    for index, (note, expected) in enumerate(cases, start=1):
        started = time.perf_counter()
        try:
            result = decider.classify(note)
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies.append(elapsed_ms)
            is_correct = result["best_choice"] == expected
            correct += is_correct

            urg_flag = "EMERGENCY" if result["is_emergency"] else "STABLE"
            print(
                f"{index}. {result['best_choice']} "
                f"expected={expected} "
                f"confidence={result['confidence']:.3f} "
                f"margin={result['margin']:.3f} "
                f"urgency={urg_flag} "
                f"latency={elapsed_ms:.0f} ms"
            )
            print(f"   note: {note}")
        except Exception as e:
            print(f"{index}. ERROR: {e}")
            print(f"   note: {note}")

    accuracy = correct / len(cases)
    print(
        f"\n{name} Results: accuracy={correct}/{len(cases)} ({accuracy:.1%}) "
        f"median_latency_ms={statistics.median(latencies) if latencies else 0:.0f}"
    )
    return accuracy

def main() -> int:
    decider = SpecialtyPolicyDecider()

    acc_orig = run_set("Original 6", ORIGINAL_CASES, decider)
    acc_new = run_set("New Holdout Set", NEW_CASES, decider)

    print(f"\nOverall Summary: Original={acc_orig:.1%}, Holdout={acc_new:.1%}")
    return 0

if __name__ == "__main__":
    import statistics
    main()
