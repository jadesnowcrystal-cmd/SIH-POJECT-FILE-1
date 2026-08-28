import random
from datetime import datetime, timedelta

District = [ "Thane","Panvel","Belapur","Seawoods","Khandeshwar","Mansarowar","Kharghar","Airoli","Kalyan","Nerul","Digagav"]
print(random.choice(District))
Date_of_report = []
range_1_start = datetime.strptime("20-08-26", "%d-%m-%y")
range_1_end = datetime.strptime("30-08-26", "%d-%m-%y")

range_2_start = datetime.strptime("01-09-26", "%d-%m-%y")
range_2_end = datetime.strptime("22-09-26", "%d-%m-%y")

# 1. Generate (August 20 to August 30)
current_date = range_1_start
while current_date <= range_1_end:
    Date_of_report.append(current_date.strftime("%d-%m-%y"))
    current_date += timedelta(days=1)

# 2. Generate  (September 1 to September 22)
current_date = range_2_start
while current_date <= range_2_end:
    Date_of_report.append(current_date.strftime("%d-%m-%y"))
    current_date += timedelta(days=1)

report_date_str = random.choice(Date_of_report)
print(report_date_str)

#Genrating Time
Time_of_report = []
start = datetime.strptime("10:00", "%H:%M")
end = datetime.strptime("23:59", "%H:%M")
step = timedelta(minutes=30)  # Change interval here as needed

current = start
while current <= end:
  Time_of_report.append(current.strftime("%H:%M"))
  current += step

report_time_str = random.choice(Time_of_report)
print(report_time_str)

#Type of Case and Planned or Unplaned
Case_type = ["Murder","Attempt to Murder","Kidnapping","Robbery"]
selection_casetype= random.choice(Case_type)

Connectivity=["Planed","Unplaned"]
selection_Connectivity= random.choice(Connectivity)
#Date of Occurrence
Date_of_Occurrence = []

# --- n ranges per case type & planned/unplanned status ---
# (min_n, max_n) — occurrence = report_date - n days
N_RANGES = {
    "Murder": {"Unplaned": (4, 7), "Planed": (7, 9)},
    "Attempt to Murder": {"Unplaned": (1, 1), "Planed": (3, 5)},
    "Kidnapping": {"Unplaned": (1, 1), "Planed": (1, 2)},
    "Robbery": {"Unplaned": (1, 1), "Planed": (1, 2)},  # treated as "theft"
}

valid_report_dates = set(Date_of_report)  # fast lookup; already excludes the Aug31 gap
report_date_dt = datetime.strptime(report_date_str, "%d-%m-%y")

min_n, max_n = N_RANGES[selection_casetype][selection_Connectivity]

occurrence_date_str = None
chosen_n = None

# Try every n from max_n down to min_n, pick the first that lands on a valid date
for n in range(max_n, min_n - 1, -1):
    candidate = report_date_dt - timedelta(days=n)
    candidate_str = candidate.strftime("%d-%m-%y")
    if candidate_str in valid_report_dates:
        occurrence_date_str = candidate_str
        chosen_n = n
        break

# Fallback: nothing in the n-range was valid (report date too close to range_1_start) -> clamp
if occurrence_date_str is None:
    occurrence_date_str = range_1_start.strftime("%d-%m-%y")
    chosen_n = (report_date_dt - range_1_start).days

Date_of_Occurrence.append(occurrence_date_str)

print(f"Case Type: {selection_casetype}")
print(f"Connectivity: {selection_Connectivity}")
#print(f"n used: {chosen_n}")#i Used for checking the code
print(f"Date of Report: {report_date_str}") #Just for checking
print(f"Date of Occurrence: {occurrence_date_str}")

Time_of_Occurrence = []

if selection_Connectivity == "Planed":
  start_too = datetime.strptime("20:00", "%H:%M")
  end_too = datetime.strptime("23:00", "%H:%M")
else:
  start_too = datetime.strptime("10:00", "%H:%M")
  end_too = datetime.strptime("23:59", "%H:%M")

step_too = timedelta(minutes=30)
current_too = start_too

while current_too <= end_too:
  Time_of_Occurrence.append(current_too.strftime("%H:%M"))
  current_too += step_too

occurrence_time_str = random.choice(Time_of_Occurrence)

#print(Time_of_Occurrence)
print(f"Occurrence Time: {occurrence_time_str}")

#Place of Occurrence
Place_of_Occurrence = []
if selection_Connectivity == "Planed":
    Coordinated_District=["Airoli","Kalyan","Nerul","Digagav"]
    Place_of_Occurrence = random.choice(Coordinated_District)
else :
    Place_of_Occurrence = random.choice(District)
print(f"Place_of_Occurrence: {Place_of_Occurrence}")

#Personal information of Particle involved
import random

# Lists of common Indian first names (split by gender) and last names
male_first_names = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Dhruv", "Kabir", "Rohan", "Rahul", "Amit", "Vikram",
    "Siddharth", "Manish", "Karan", "Nikhil"
]

female_first_names = [
    "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Anika", "Navya", "Angel",
    "Riya", "Pooja", "Neha", "Priya", "Anjali", "Sneha", "Kavita", "Meera",
    "Swati", "Divya", "Kiran", "Tanvi"
]

last_names = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Bansal", "Mehta", "Patel", "Reddy",
    "Nair", "Iyer", "Joshi", "Deshmukh", "Choudhury", "Das", "Sen", "Bose",
    "Chatterjee", "Mukherjee", "Singh", "Kumar"
]
male_planned_first_names = [
    "Mogambo",
    "Shakaal",
    "Kancha",
    "Gabbar",
    "Don",
    "Teja",
    "Crime Master"
]
female_planned_first_names = [
    "Komolika",
    "Simran", # Wait, she's nice... let's use:
    "Madame",
    "Bindoo",
    "Kaminey"
]
last_planned_names = [
    "The Don",
    "Dang",
    "Cheena",
    "Singh",
    "Gogo",
    "Pathan",
    "Sinha",
    "Bihari"
]

Occupation_Unplaned=["Software Engineer",
    "Data Analyst",
    "Doctor",
    "Teacher",
    "Accountant",
    "Civil Engineer",
    "Graphic Designer",
    "Marketing Manager",
    "Nurse",
    "Banker",
    "Lawyer",
    "Architect",
    "Pharmacist",
    "Chef",
    "Mechanical Engineer",
    "Content Writer",
    "HR Specialist",
    "Sales Executive",
    "Research Scientist",
    "Project Manager"]

Occupation_planed=["Section Officer" ,"Tax Assistant","Junior Engineer","Postal Inspector","Revenue Inspector","Lower Division"," Clerk", 'Panchayat Secretary']
def generate_person():
    gender = random.choice(['Male', 'Female'])

    if gender == 'Male':
        first_name = random.choice(male_first_names)
    else:
        first_name = random.choice(female_first_names)

    last_name = random.choice(last_names)
    full_name = f"{first_name} {last_name}"
    age = random.randint(22, 78)
    father_name = f"{random.choice(male_first_names)} {last_name}"
    if gender == 'Male':
        suppose_name = f"{random.choice(female_first_names)} {random.choice(last_names)}"
    else :
        suppose_name = f"{random.choice(male_first_names)} {random.choice(last_names)}"
    if selection_Connectivity == "Planed":
        occupation = random.choice(Occupation_planed)
    else:
        occupation = random.choice(Occupation_Unplaned)
    #Genration of Phone numbers
    def generate_phone_number():
        # Generate random area code (200-999)
        area_code = random.randint(700, 999)

        # Generate random 3-digit prefix (200-999)
        prefix = random.randint(200, 999)

        # Generate random 4-digit line number (0000-9999)
        line_number = random.randint(0, 9999)

        # Format as (XXX) XXX-XXXX
        phone_number = f"({area_code}) {prefix}-{line_number:04d}"
        return phone_number
    if selection_Connectivity == "Planed":
        address = random.choice(Coordinated_District)
    else :
        address = random.choice(District)
    # Genrating fake Adhaar no
    def generate_dummy_aadhaar():
        # Generate 12 random digits
        digits = [str(random.randint(0, 9)) for _ in range(12)]

        # Optional: Aadhaar usually doesn't start with 0 or 1, let's make the first digit 2-9 for realism
        digits[0] = str(random.randint(2, 9))

        # Join into a single string
        raw_number = "".join(digits)

        # Format as XXXX XXXX XXXX
        formatted_aadhaar = f"{raw_number[0:4]} {raw_number[4:8]} {raw_number[8:12]}"

        return formatted_aadhaar

    return {
        "Name": full_name,
        "Age": age,
        "Gender": gender,
        "Fathers name" : father_name,
        "Suppose name" : suppose_name,
        "Occupation" : occupation,
        "Address" : address,
        "Phone number" : generate_phone_number(),
        "Aadhaar Card" : generate_dummy_aadhaar()

    }


# Generate and print a single random person record
Informant = generate_person()
print("Informant Details")

print(f"{'Full Name':<21} | {'Age':<5} | {'Gender':<6} | {'Fathers name':<21} | {'Suppose name':<21} | {'Occupation':<21} | {'Phone number':<12} | {'Address':<19} | {'Aadhaar Card':<15}")
print("-" * 208)
print(f"{Informant['Name']:<21} | { Informant['Age']:<5} | {Informant['Gender']:<6} | { Informant['Fathers name']:<21} | {Informant['Suppose name']:<21} | { Informant['Occupation']:<21} | {Informant['Phone number']:<12} | { Informant['Address']:<19} | { Informant['Aadhaar Card']:<15}")

Witness = generate_person()
print("Witness Details")

print(f"{'Full Name':<21} | {'Age':<5} | {'Gender':<6} | {'Fathers name':<21} | {'Suppose name':<21} | {'Occupation':<21} | {'Phone number':<12} | {'Address':<19} | {'Aadhaar Card':<15}")
print("-" * 208)
print(f"{Witness['Name']:<21} | { Witness['Age']:<5} | {Witness['Gender']:<6} | { Witness['Fathers name']:<21} | {Witness['Suppose name']:<21} | { Witness['Occupation']:<21} | {Witness['Phone number']:<12} | {Witness ['Address']:<19} | { Witness['Aadhaar Card']:<15}")
print("-" * 208)
print(f"{'Date of Presence':<21} | {'Time of Presence':<21} | {'Place of Presence':<21} ")
print("-" * 65)
print(f"{occurrence_date_str :<15} | {occurrence_time_str :<25} | {Place_of_Occurrence :<25}")
print("-" * 208)
Victim = generate_person()

print("Victim Details")
print(f"{'Full Name':<21} | {'Age':<5} | {'Gender':<6} | {'Fathers name':<21} | {'Suppose name':<21} | {'Occupation':<21} | {'Phone number':<12} | {'Address':<19} | {'Aadhaar Card':<15}")
print("-" * 208)
print(f"{Victim['Name']:<21} | {Victim['Age']:<5} | {Victim['Gender']:<6} | { Victim['Fathers name']:<21} | {Victim['Suppose name']:<21} | { Victim['Occupation']:<21} | {Victim['Phone number']:<12} | { Victim['Address']:<19} | {Victim['Aadhaar Card']:<15}")

#Acuused details
def accused_person():
    gender = random.choice(['Male', 'Female'])

    if gender == 'Male':
        first_name = random.choice(male_planned_first_names)
    else:
        first_name = random.choice(female_planned_first_names)

    last_name = random.choice(last_planned_names)
    full_name = f"{first_name} {last_name}"
    age = random.randint(22, 78)
    father_name = f"{random.choice(male_first_names)} {last_name}"
    if gender == 'Male':
        suppose_name = f"{random.choice(female_first_names)} {random.choice(last_names)}"
    else :
        suppose_name = f"{random.choice(male_first_names)} {random.choice(last_names)}"
    if selection_Connectivity == "Planed":
        occupation = random.choice(Occupation_planed)
    else:
        occupation = random.choice(Occupation_Unplaned)
    #Genration of Phone numbers
    def generate_phone_number():
        # Generate random area code (200-999)
        area_code = random.randint(700, 999)

        # Generate random 3-digit prefix (200-999)
        prefix = random.randint(200, 999)

        # Generate random 4-digit line number (0000-9999)
        line_number = random.randint(0, 9999)

        # Format as (XXX) XXX-XXXX
        phone_number = f"({area_code}) {prefix}-{line_number:04d}"
        return phone_number
    if selection_Connectivity == "Planed":
        address = random.choice(Coordinated_District)
    else :
        address = random.choice(District)
    # Genrating fake Adhaar no
    def generate_dummy_aadhaar():
        # Generate 12 random digits
        digits = [str(random.randint(0, 9)) for _ in range(12)]

        # Optional: Aadhaar usually doesn't start with 0 or 1, let's make the first digit 2-9 for realism
        digits[0] = str(random.randint(2, 9))

        # Join into a single string
        raw_number = "".join(digits)

        # Format as XXXX XXXX XXXX
        formatted_aadhaar = f"{raw_number[0:4]} {raw_number[4:8]} {raw_number[8:12]}"

        return formatted_aadhaar

    return {
        "Name": full_name,
        "Age": age,
        "Gender": gender,
        "Fathers name" : father_name,
        "Suppose name" : suppose_name,
        "Occupation" : occupation,
        "Address" : address,
        "Phone number" : generate_phone_number(),
        "Aadhaar Card" : generate_dummy_aadhaar()

    }
print("Accused Details")
Probability=[1, 0]
if random.choice(Probability) == 1:
    Acussed = accused_person()
    print(
        f"{'Full Name':<21} | {'Age':<5} | {'Gender':<6} | {'Fathers name':<21} | {'Suppose name':<21} | {'Occupation':<21} | {'Phone number':<12} | {'Address':<19} | {'Aadhaar Card':<15}")
    print("-" * 208)
    print(
        f"{Acussed['Name']:<21} | {Acussed['Age']:<5} | {Acussed['Gender']:<6} | { Acussed['Fathers name']:<21} | {Acussed['Suppose name']:<21} | {Acussed['Occupation']:<21} | {Acussed['Phone number']:<12} |  | { Acussed['Address']:<19} | {Acussed['Aadhaar Card']:<15}")
else :
    print(
        f"{'Full Name':<19} | {'Age':<19} | {'Gender':<19} | {'Fathers name':<19} | {'Suppose name':<19} | {'Occupation':<19} | {'Phone number':<19} | {'Address':<19} | {'Aadhaar Card':<19}")
    print("-" * 208)
    print(
        f"{'Unknow':<19} | {'Unknow ':<19} | {'Unknow':<19} | {'Unknow':<19} | {'Unknow':<19} | {'Unknow':<19} | {'Unknow':<19} | {'Unknow':<19} | {'Unknow':<19}")
    print("-" * 208)
