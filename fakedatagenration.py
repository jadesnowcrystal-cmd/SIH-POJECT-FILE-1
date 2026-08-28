iimport random
import json
from datetime import datetime, timedelta


DISTRICTS = [
    "Thane", "Panvel", "Belapur", "Seawoods", "Khandeshwar", 
    "Mansarowar", "Kharghar", "Airoli", "Kalyan", "Nerul", "Digagav"
]

COORDINATED_DISTRICTS = ["Airoli", "Kalyan", "Nerul", "Digagav"]

CASE_TYPES = ["Murder", "Attempt to Murder", "Kidnapping", "Robbery"]
CONNECTIVITY_TYPES = ["Planed", "Unplaned"]

# Occurrence date offset ranges relative to Report Date
N_RANGES = {
    "Murder": {"Unplaned": (4, 7), "Planed": (7, 9)},
    "Attempt to Murder": {"Unplaned": (1, 1), "Planed": (3, 5)},
    "Kidnapping": {"Unplaned": (1, 1), "Planed": (1, 2)},
    "Robbery": {"Unplaned": (1, 1), "Planed": (1, 2)},
}

MALE_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Dhruv", "Kabir", "Rohan", "Rahul", "Amit", "Vikram",
    "Siddharth", "Manish", "Karan", "Nikhil"
]

FEMALE_FIRST_NAMES = [
    "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Anika", "Navya", "Angel",
    "Riya", "Pooja", "Neha", "Priya", "Anjali", "Sneha", "Kavita", "Meera",
    "Swati", "Divya", "Kiran", "Tanvi"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Bansal", "Mehta", "Patel", "Reddy",
    "Nair", "Iyer", "Joshi", "Deshmukh", "Choudhury", "Das", "Sen", "Bose",
    "Chatterjee", "Mukherjee", "Singh", "Kumar"
]

MALE_PLANNED_NAMES = ["Mogambo", "Shakaal", "Kancha", "Gabbar", "Don", "Teja", "Crime Master"]
FEMALE_PLANNED_NAMES = ["Komolika", "Madame", "Bindoo", "Kaminey"]
LAST_PLANNED_NAMES = ["The Don", "Dang", "Cheena", "Singh", "Gogo", "Pathan", "Sinha", "Bihari"]

OCCUPATIONS_UNPLANNED = [
    "Software Engineer", "Data Analyst", "Doctor", "Teacher", "Accountant",
    "Civil Engineer", "Graphic Designer", "Marketing Manager", "Nurse", "Banker",
    "Lawyer", "Architect", "Pharmacist", "Chef", "Mechanical Engineer",
    "Content Writer", "HR Specialist", "Sales Executive", "Research Scientist", "Project Manager"
]

OCCUPATIONS_PLANNED = [
    "Section Officer", "Tax Assistant", "Junior Engineer", "Postal Inspector",
    "Revenue Inspector", "Lower Division Clerk", "Panchayat Secretary"
]

# ==========================================
# HELPER GENERATORS
# ==========================================
def generate_phone_number():
    area_code = random.randint(700, 999)
    prefix = random.randint(200, 999)
    line_number = random.randint(0, 9999)
    return f"({area_code}) {prefix}-{line_number:04d}"

def generate_dummy_aadhaar():
    digits = [str(random.randint(0, 9)) for _ in range(12)]
    digits[0] = str(random.randint(2, 9))
    raw_number = "".join(digits)
    return f"{raw_number[0:4]} {raw_number[4:8]} {raw_number[8:12]}"

def generate_person(role="general", connectivity="Unplaned"):
    """Generates standardized person demographic profile."""
    gender = random.choice(['Male', 'Female'])
    
    if role == "accused":
        first_name = random.choice(MALE_PLANNED_NAMES if gender == 'Male' else FEMALE_PLANNED_NAMES)
        last_name = random.choice(LAST_PLANNED_NAMES)
    else:
        first_name = random.choice(MALE_FIRST_NAMES if gender == 'Male' else FEMALE_FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

    full_name = f"{first_name} {last_name}"
    age = random.randint(22, 78)
    father_name = f"{random.choice(MALE_FIRST_NAMES)} {last_name}"
    
    spouse_first = random.choice(FEMALE_FIRST_NAMES if gender == 'Male' else MALE_FIRST_NAMES)
    spouse_name = f"{spouse_first} {random.choice(LAST_NAMES)}"
    
    occupation = random.choice(OCCUPATIONS_PLANNED if connectivity == "Planed" else OCCUPATIONS_UNPLANNED)
    address = random.choice(COORDINATED_DISTRICTS if connectivity == "Planed" else DISTRICTS)

    return {
        "person_id": f"PER-{random.randint(10000, 99999)}",
        "name": full_name,
        "age": age,
        "gender": gender,
        "father_name": father_name,
        "spouse_name": spouse_name,
        "occupation": occupation,
        "address": address,
        "phone_number": generate_phone_number(),
        "aadhaar_card": generate_dummy_aadhaar()
    }

# ==========================================
# MAIN FIR CASE GENERATOR
# ==========================================
def generate_fir_case(case_idx=1):
    """Generates a fully interconnected synthetic case dataset."""
    district = random.choice(DISTRICTS)
    
    # 1. Generate Report Date
    date_pool = []
    r1_start, r1_end = datetime.strptime("20-08-26", "%d-%m-%y"), datetime.strptime("30-08-26", "%d-%m-%y")
    r2_start, r2_end = datetime.strptime("01-09-26", "%d-%m-%y"), datetime.strptime("22-09-26", "%d-%m-%y")

    curr = r1_start
    while curr <= r1_end:
        date_pool.append(curr)
        curr += timedelta(days=1)

    curr = r2_start
    while curr <= r2_end:
        date_pool.append(curr)
        curr += timedelta(days=1)

    report_dt = random.choice(date_pool)
    report_date_str = report_dt.strftime("%d-%m-%y")

    # 2. Generate Report Time
    report_times = []
    curr_time = datetime.strptime("10:00", "%H:%M")
    end_time = datetime.strptime("23:59", "%H:%M")
    while curr_time <= end_time:
        report_times.append(curr_time.strftime("%H:%M"))
        curr_time += timedelta(minutes=30)
    report_time_str = random.choice(report_times)

    # 3. Case Characteristics
    case_type = random.choice(CASE_TYPES)
    connectivity = random.choice(CONNECTIVITY_TYPES)

    # 4. Occurrence Date Calculation
    min_n, max_n = N_RANGES[case_type][connectivity]
    occurrence_date_str = None

    valid_date_strs = set([d.strftime("%d-%m-%y") for d in date_pool])
    for n in range(max_n, min_n - 1, -1):
        candidate = report_dt - timedelta(days=n)
        candidate_str = candidate.strftime("%d-%m-%y")
        if candidate_str in valid_date_strs:
            occurrence_date_str = candidate_str
            break

    if not occurrence_date_str:
        occurrence_date_str = r1_start.strftime("%d-%m-%y")

    # 5. Occurrence Time
    occ_times = []
    curr_occ = datetime.strptime("20:00" if connectivity == "Planed" else "10:00", "%H:%M")
    end_occ = datetime.strptime("23:00" if connectivity == "Planed" else "23:59", "%H:%M")
    while curr_occ <= end_occ:
        occ_times.append(curr_occ.strftime("%H:%M"))
        curr_occ += timedelta(minutes=30)
    occurrence_time_str = random.choice(occ_times)

    # 6. Place of Occurrence
    place_of_occurrence = random.choice(COORDINATED_DISTRICTS if connectivity == "Planed" else DISTRICTS)

    # 7. Generate Person Entities
    informant = generate_person("general", connectivity)
    witness = generate_person("general", connectivity)
    victim = generate_person("general", connectivity)
    
    # 50% probability of known vs unknown accused
    accused_known = random.choice([True, False])
    accused = generate_person("accused", connectivity) if accused_known else None

    # Construct unified JSON payload
    fir_record = {
        "case_id": f"FIR-2026-{case_idx:04d}",
        "district": district,
        "case_type": case_type,
        "connectivity": connectivity,
        "report_details": {
            "date": report_date_str,
            "time": report_time_str
        },
        "occurrence_details": {
            "date": occurrence_date_str,
            "time": occurrence_time_str,
            "place": place_of_occurrence
        },
        "entities": {
            "informant": informant,
            "witness": witness,
            "victim": victim,
            "accused": accused if accused_known else "UNKNOWN"
        }
    }
    return fir_record

def generate_fir_dataset(num_records=5):
    """Generates a list of FIR case records."""
    return [generate_fir_case(i + 1) for i in range(num_records)]


if __name__ == "__main__":
    sample_dataset = generate_fir_dataset(num_records=1)
    print(json.dumps(sample_dataset, indent=2))
