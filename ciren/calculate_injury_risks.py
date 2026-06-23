"""
CIREN Crash Data - Injury Risk Calculation Script

This script calculates injury risks for filtered crash cases using the 
CISS injury risk models (logistic regression).

The models predict the probability of:
- Head AIS 3+ injuries
- Chest AIS 3+ injuries  
- Lower Extremity AIS 2+ injuries

For different crash directions:
- Frontal (0 degrees)
- Oblique Combined
- Oblique Left
- Oblique Right
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

class InjuryRiskModel:
    """
    Implements CISS injury risk models using logistic regression.
    
    Risk = 1 / (1 + exp(-z))
    where z = intercept + sum(coefficient_i * variable_i)
    """
    
    def __init__(self, model_file_path):
        """
        Load model coefficients from Excel file.
        
        Parameters:
        -----------
        model_file_path : str
            Path to the CISS injury models Excel file
        """
        self.model_file = model_file_path
        self.coefficients = self._load_coefficients()
        
    def _load_coefficients(self):
        """Load model coefficients from the Excel file."""
        df = pd.read_excel(self.model_file, sheet_name='Model Coefficients')
        
        # Extract coefficients for each injury type and direction
        coeffs = {
            'Head': {},
            'Chest': {},
            'LowerExtremity': {}
        }
        
        # Head AIS 3+ models (columns 0-5)
        coeffs['Head']['Frontal'] = {
            'Intercept': df.iloc[1, 1],
            'LDVMPH': df.iloc[2, 1],
            'Age_36_65': df.iloc[4, 1],
            'Age_66+': df.iloc[5, 1],
            'Height': df.iloc[6, 1],
            'BMI': df.iloc[7, 1],
            'Sex_F': df.iloc[8, 1],
        }
        
        coeffs['Head']['Oblique_Combined'] = {
            'Intercept': df.iloc[1, 2],
            'LDVMPH': df.iloc[2, 2],
            'Age_36_65': df.iloc[4, 2],
            'Age_66+': df.iloc[5, 2],
            'Height': df.iloc[6, 2],
            'BMI': df.iloc[7, 2],
            'Sex_F': df.iloc[8, 2],
            'PDOF_R': df.iloc[10, 2],
        }
        
        coeffs['Head']['Oblique_Left'] = {
            'Intercept': df.iloc[1, 3],
            'LDVMPH': df.iloc[2, 3],
            'Age_36_65': df.iloc[4, 3],
            'Age_66+': df.iloc[5, 3],
            'Height': df.iloc[6, 3],
            'BMI': df.iloc[7, 3],
            'Sex_F': df.iloc[8, 3],
        }
        
        coeffs['Head']['Oblique_Right'] = {
            'Intercept': df.iloc[1, 4],
            'LDVMPH': df.iloc[2, 4],
            'Age_36_65': df.iloc[4, 4],
            'Age_66+': df.iloc[5, 4],
            'Height': df.iloc[6, 4],
            'BMI': df.iloc[7, 4],
            'Sex_F': df.iloc[8, 4],
        }
        
        # Chest AIS 3+ models (columns 6-11)
        coeffs['Chest']['Frontal'] = {
            'Intercept': df.iloc[1, 7],
            'LDVMPH': df.iloc[2, 7],
            'Age_36_65': df.iloc[4, 7],
            'Age_66+': df.iloc[5, 7],
            'Height': df.iloc[6, 7],
            'BMI': df.iloc[7, 7],
            'Sex_F': df.iloc[8, 7],
        }
        
        coeffs['Chest']['Oblique_Combined'] = {
            'Intercept': df.iloc[1, 8],
            'LDVMPH': df.iloc[2, 8],
            'Age_36_65': df.iloc[4, 8],
            'Age_66+': df.iloc[5, 8],
            'Height': df.iloc[6, 8],
            'BMI': df.iloc[7, 8],
            'Sex_F': df.iloc[8, 8],
            'PDOF_R': df.iloc[10, 8],
        }
        
        coeffs['Chest']['Oblique_Left'] = {
            'Intercept': df.iloc[1, 9],
            'LDVMPH': df.iloc[2, 9],
            'Age_36_65': df.iloc[4, 9],
            'Age_66+': df.iloc[5, 9],
            'Height': df.iloc[6, 9],
            'BMI': df.iloc[7, 9],
            'Sex_F': df.iloc[8, 9],
        }
        
        coeffs['Chest']['Oblique_Right'] = {
            'Intercept': df.iloc[1, 10],
            'LDVMPH': df.iloc[2, 10],
            'Age_36_65': df.iloc[4, 10],
            'Age_66+': df.iloc[5, 10],
            'Height': df.iloc[6, 10],
            'BMI': df.iloc[7, 10],
            'Sex_F': df.iloc[8, 10],
        }
        
        # Lower Extremity AIS 2+ models (columns 12-16)
        coeffs['LowerExtremity']['Frontal'] = {
            'Intercept': df.iloc[1, 13],
            'LDVMPH': df.iloc[2, 13],
            'Age_36_65': df.iloc[4, 13],
            'Age_66+': df.iloc[5, 13],
            'Height': df.iloc[6, 13],
            'BMI': df.iloc[7, 13],
            'Sex_F': df.iloc[8, 13],
        }
        
        coeffs['LowerExtremity']['Oblique_Combined'] = {
            'Intercept': df.iloc[1, 14],
            'LDVMPH': df.iloc[2, 14],
            'Age_36_65': df.iloc[4, 14],
            'Age_66+': df.iloc[5, 14],
            'Height': df.iloc[6, 14],
            'BMI': df.iloc[7, 14],
            'Sex_F': df.iloc[8, 14],
            'PDOF_R': df.iloc[10, 14],
        }
        
        coeffs['LowerExtremity']['Oblique_Left'] = {
            'Intercept': df.iloc[1, 15],
            'LDVMPH': df.iloc[2, 15],
            'Age_36_65': df.iloc[4, 15],
            'Age_66+': df.iloc[5, 15],
            'Height': df.iloc[6, 15],
            'BMI': df.iloc[7, 15],
            'Sex_F': df.iloc[8, 15],
        }
        
        coeffs['LowerExtremity']['Oblique_Right'] = {
            'Intercept': df.iloc[1, 16],
            'LDVMPH': df.iloc[2, 16],
            'Age_36_65': df.iloc[4, 16],
            'Age_66+': df.iloc[5, 16],
            'Height': df.iloc[6, 16],
            'BMI': df.iloc[7, 16],
            'Sex_F': df.iloc[8, 16],
        }
        
        return coeffs
    
    def _determine_direction(self, clock_direction):
        """
        Determine crash direction category from clock direction.
        
        Parameters:
        -----------
        clock_direction : float or str
            Clock direction in degrees (0-360) or as string
            
        Returns:
        --------
        str : One of ['Frontal', 'Oblique_Left', 'Oblique_Right', 'Oblique_Combined']
        """
        if pd.isna(clock_direction):
            return 'Frontal'  # Default
        
        # Convert to float if string
        try:
            angle = float(clock_direction)
        except:
            return 'Frontal'
        
        # Normalize to 0-360
        angle = angle % 360
        
        # Frontal: 330-30 degrees (11 o'clock to 1 o'clock)
        if angle >= 330 or angle <= 30:
            return 'Frontal'
        # Oblique Left: 30-150 degrees
        elif 30 < angle <= 150:
            return 'Oblique_Left'
        # Rear: 150-210 degrees (not typically modeled)
        elif 150 < angle <= 210:
            return 'Oblique_Combined'  # Use combined for rear
        # Oblique Right: 210-330 degrees
        else:
            return 'Oblique_Right'
    
    def calculate_risk(self, case_data, injury_type, direction):
        """
        Calculate injury risk for a specific case, injury type, and direction.
        
        Parameters:
        -----------
        case_data : dict or pd.Series
            Case data containing required variables
        injury_type : str
            One of ['Head', 'Chest', 'LowerExtremity']
        direction : str
            One of ['Frontal', 'Oblique_Left', 'Oblique_Right', 'Oblique_Combined']
            
        Returns:
        --------
        float : Injury risk probability (0-1)
        """
        # Get coefficients for this model
        coeffs = self.coefficients[injury_type][direction]
        
        # Start with intercept
        z = coeffs['Intercept']
        
        # Add log(delta-V in mph)
        delta_v_mph = case_data.get('total_delta_v', np.nan)
        if pd.notna(delta_v_mph) and delta_v_mph > 0:
            z += coeffs['LDVMPH'] * np.log(delta_v_mph)
        else:
            # If no delta-V, use a default value (25 mph)
            z += coeffs['LDVMPH'] * np.log(25)
        
        # Age effects (reference group is 18-35)
        age = case_data.get('age', 30)
        if 36 <= age <= 65:
            z += coeffs['Age_36_65']
        elif age > 65:
            z += coeffs['Age_66+']
        
        # Height (in cm)
        height = case_data.get('height', 170)  # Default 170 cm
        if pd.notna(height):
            z += coeffs['Height'] * height
        
        # BMI
        bmi = case_data.get('bmi', 25)  # Calculate from height/weight if needed
        if pd.isna(bmi):
            height_m = height / 100 if pd.notna(height) else 1.7
            weight = case_data.get('weight', 70)
            if pd.notna(weight):
                bmi = weight / (height_m ** 2)
            else:
                bmi = 25  # Default
        z += coeffs['BMI'] * bmi
        
        # Sex (Female = 1, Male = 0)
        gender = case_data.get('gender', 'M')
        if gender == 'F':
            z += coeffs['Sex_F']
        
        # PDOF (Principal Direction of Force) - only for Oblique Combined
        if direction == 'Oblique_Combined' and 'PDOF_R' in coeffs:
            # This would require knowing left vs right impact
            # For now, assume 0 (left reference)
            z += coeffs['PDOF_R'] * 0
        
        # Calculate probability using logistic function
        risk = 1 / (1 + np.exp(-z))
        
        return risk
    
    def calculate_all_risks(self, case_data):
        """
        Calculate all injury risks for a case.
        
        Parameters:
        -----------
        case_data : dict or pd.Series
            Case data containing required variables
            
        Returns:
        --------
        dict : Dictionary with all injury risks
        """
        # Determine direction
        direction = self._determine_direction(case_data.get('primary_pdof_deg', 0))
        
        results = {
            'direction': direction,
            'Head_Frontal': self.calculate_risk(case_data, 'Head', 'Frontal'),
            'Head_Oblique_Combined': self.calculate_risk(case_data, 'Head', 'Oblique_Combined'),
            'Head_Oblique_Left': self.calculate_risk(case_data, 'Head', 'Oblique_Left'),
            'Head_Oblique_Right': self.calculate_risk(case_data, 'Head', 'Oblique_Right'),
            'Chest_Frontal': self.calculate_risk(case_data, 'Chest', 'Frontal'),
            'Chest_Oblique_Combined': self.calculate_risk(case_data, 'Chest', 'Oblique_Combined'),
            'Chest_Oblique_Left': self.calculate_risk(case_data, 'Chest', 'Oblique_Left'),
            'Chest_Oblique_Right': self.calculate_risk(case_data, 'Chest', 'Oblique_Right'),
            'LowerExtremity_Frontal': self.calculate_risk(case_data, 'LowerExtremity', 'Frontal'),
            'LowerExtremity_Oblique_Combined': self.calculate_risk(case_data, 'LowerExtremity', 'Oblique_Combined'),
            'LowerExtremity_Oblique_Left': self.calculate_risk(case_data, 'LowerExtremity', 'Oblique_Left'),
            'LowerExtremity_Oblique_Right': self.calculate_risk(case_data, 'LowerExtremity', 'Oblique_Right'),
        }
        
        # Add the most appropriate risk for the actual direction
        results['Head_Risk'] = results[f'Head_{direction}']
        results['Chest_Risk'] = results[f'Chest_{direction}']
        results['LowerExtremity_Risk'] = results[f'LowerExtremity_{direction}']
        
        return results


def parse_numeric(value):
    """Parse numeric value from string format."""
    if pd.isna(value):
        return np.nan
    
    # If already numeric, return it
    if isinstance(value, (int, float)):
        return float(value)
    
    # Convert to string and extract numbers
    value_str = str(value)
    
    # Handle "Unknown" or similar
    if 'unknown' in value_str.lower() or 'n/a' in value_str.lower():
        return np.nan
    
    # Extract first number (handles formats like "185 cms ( 73 in )")
    import re
    match = re.search(r'(\d+\.?\d*)', value_str)
    if match:
        return float(match.group(1))
    
    return np.nan


def calculate_bmi(height_cm, weight_kg):
    """Calculate BMI from height and weight."""
    height_cm = parse_numeric(height_cm)
    weight_kg = parse_numeric(weight_kg)
    
    if pd.isna(height_cm) or pd.isna(weight_kg) or height_cm <= 0 or weight_kg <= 0:
        return np.nan
    
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)


def main():
    """Main execution function."""
    
    print("="*80)
    print("CIREN Crash Data - Injury Risk Calculation")
    print("="*80)
    
    # File paths
    cases_file = rf'ciren_database/master_cases.xlsx'  # the excel file with the scraped ciren dataset
    model_file = 'ciren/CISS_injury_models_20210415.xlsx'
    output_dir = Path('outputs')
    output_dir.mkdir(parents=True, exist_ok = True)
    
    # 1. Load the filtered cases data
    print("\n1. Loading filtered cases data...")
    df_cases = pd.read_excel(cases_file)
    print(f"   Loaded {len(df_cases)} cases")
    
    # Parse numeric fields
    print("\n2. Parsing numeric fields...")
    df_cases['age_yr'] = df_cases['age_yr'].apply(parse_numeric)
    df_cases['height'] = df_cases['height'].apply(parse_numeric)
    df_cases['weight'] = df_cases['weight'].apply(parse_numeric)
    df_cases['total_delta_v'] = df_cases['edr_total_delta_v_kmph'].apply(parse_numeric)
    
    # Convert delta-V from km/h to mph 
    print("   Converting delta-V from km/h to mph...")
    df_cases['total_delta_v'] = df_cases['edr_total_delta_v_kmph'] * 0.621371
    
    print(f"   Parsed numeric fields")
    
    # 3. Calculate BMI where needed
    print("\n3. Calculating BMI for cases...")
    df_cases['bmi'] = df_cases.apply(
        lambda row: calculate_bmi(row['height'], row['weight']), 
        axis=1
    )
    
    # Fill missing BMI with median
    bmi_median = df_cases['bmi'].median()
    if pd.isna(bmi_median):
        bmi_median = 25.0  # Default if all missing
    df_cases['bmi'].fillna(bmi_median, inplace=True)
    print(f"   BMI calculated (median for missing: {bmi_median:.1f})")
    
    # 4. Initialize injury risk model
    print("\n4. Loading injury risk models...")
    model = InjuryRiskModel(model_file)
    print("   Models loaded successfully")
    
    # 5. Calculate injury risks for all cases
    print("\n5. Calculating injury risks for all cases...")
    
    results_list = []
    for idx, row in df_cases.iterrows():
        # Calculate all risks
        risks = model.calculate_all_risks(row)
        
        # Combine with case info
        result = {
            'cirenid': row['cirenid'],
            'category': row['scenario'],
            # 'severity_level': row['severity_level'],
            'age_yr': row['age_yr'],
            'gender': row['sex'],
            'height': row['height'],
            'weight': row['weight'],
            'bmi': row['bmi'],
            'delta_v': row['edr_total_delta_v_kmph'],
            'iss': row['iss'],
            **risks
        }
        results_list.append(result)
    
    df_results = pd.DataFrame(results_list)
    print(f"   Calculated risks for {len(df_results)} cases")
    
    # 6. Save results to CSV
    print("\n6. Saving results...")
    output_csv = output_dir / 'injury_risk_calculations.csv'
    df_results.to_csv(output_csv, index=False)
    print(f"   Saved to: {output_csv}")


if __name__ == "__main__":
    results = main()
