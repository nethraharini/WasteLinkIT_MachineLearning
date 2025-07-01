import pandas as pd
import numpy as np

# Monthly date range from Jan 2018 to Dec 2024
date_range = pd.date_range(start="2018-01-01", end="2024-12-01", freq="MS")

# 2011 Census population in lakhs, projected to 2024
district_pop_2011 = {
    "Ariyalur": 7.5, "Chengalpattu": 12.5, "Chennai": 46.8, "Coimbatore": 34.5, "Cuddalore": 26.0,
    "Dharmapuri": 15.0, "Dindigul": 21.5, "Erode": 22.8, "Kallakurichi": 13.2, "Kancheepuram": 23.0,
    "Kanyakumari": 19.0, "Karur": 10.6, "Krishnagiri": 18.8, "Madurai": 30.4, "Mayiladuthurai": 8.6,
    "Nagapattinam": 16.2, "Namakkal": 17.2, "Nilgiris": 7.3, "Perambalur": 5.6, "Pudukkottai": 16.1,
    "Ramanathapuram": 13.5, "Ranipet": 12.4, "Salem": 34.2, "Sivaganga": 13.4, "Tenkasi": 14.0,
    "Thanjavur": 24.0, "Theni": 12.6, "Thoothkudi": 17.5, "Tiruchirappalli": 27.2, "Tirunelveli": 27.5,
    "Tirupathur": 10.1, "Tiruppur": 24.5, "Tiruvallur": 27.8, "Tiruvannamalai": 24.5,
    "Tiruvarur": 12.5, "Vellore": 22.0, "Viluppuram": 29.5, "Virudhunagar": 20.0
}

# Annual population growth rate
growth_rate = 0.012

# Plastic waste per capita (kg/day)
min_waste = 0.025
max_waste = 0.05

# Plastic type distribution
plastic_type_ratios = {
    "PET": 0.25,
    "HDPE": 0.15,
    "PVC": 0.10,
    "LDPE": 0.20,
    "PP": 0.20,
    "PS": 0.10
}

# Generate rows
rows = []

for district, pop_2011 in district_pop_2011.items():
    for date in date_range:
        years_since_2011 = date.year - 2011
        projected_pop = pop_2011 * (1 + growth_rate) ** years_since_2011 * 100000  # Convert lakhs to number

        # Base per capita waste (with small variation)
        base_waste = np.random.uniform(min_waste, max_waste)

        # Seasonality factor
        month_factor = 1.0
        if date.month in [10, 11]:
            month_factor = 1.2  # Festival
        elif date.month in [6, 7]:
            month_factor = 0.9  # Monsoon
        elif date.month in [4, 5] and district in ["Nilgiris", "Kanyakumari", "Madurai"]:
            month_factor = 1.3  # Summer tourism

        # Monthly total waste
        days_in_month = pd.Period(date.strftime('%Y-%m')).days_in_month
        total_waste_kg = projected_pop * base_waste * days_in_month * month_factor
        total_waste_tons = total_waste_kg / 1000  # Convert to tons

        # Breakdown by plastic type
        waste_breakdown = {
            f"{ptype}_Tons": round(total_waste_tons * ratio, 2)
            for ptype, ratio in plastic_type_ratios.items()
        }

        rows.append({
            "District": district,
            "Month": date.strftime("%Y-%m"),
            "Total_Waste_Tons": round(total_waste_tons, 2),
            **waste_breakdown
        })

# Final DataFrame
df = pd.DataFrame(rows)

# Save to CSV
output_path = "tn_realistic_plastic_waste_2018_2024.csv"
df.to_csv(output_path, index=False)
print(f"✅ Dataset saved as: {output_path}")
