from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
# Load credentials from environment or file
if os.getenv('GOOGLE_CREDENTIALS'):
    creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
    # Fix newlines in private_key
    if 'private_key' in creds_dict:
        creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
else:
    creds = Credentials.from_service_account_file("cred.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = os.getenv('SHEET_ID', "1Gj9a6yZb3zGnwfLcqkW7MEDNihLSu0QoYqubCUe68yo")
spreadsheet = client.open_by_key(sheet_id)

# Members list
MEMBERS = [
    # Yudhishthira Team (5)
    {"name": "HG Ārādhan Pr", "team": "Yudhishthira"},
    {"name": "Tanmay Pr", "team": "Yudhishthira"},
    {"name": "Rohit Pr", "team": "Yudhishthira"},
    {"name": "Amol Pr", "team": "Yudhishthira"},
    {"name": "Anish Pr", "team": "Yudhishthira"},
    # Bhima Team (5)
    {"name": "Abhishek Pr", "team": "Bhima"},
    {"name": "Hemant Pr", "team": "Bhima"},
    {"name": "Āditya M. Pr", "team": "Bhima"},
    {"name": "Shantanu Pr", "team": "Bhima"},
    {"name": "Vedānt S. Pr", "team": "Bhima"},
    # Arjuna Team (12)
    {"name": "Chaitanya Pr", "team": "Arjuna"},
    {"name": "Achintya Pr", "team": "Arjuna"},
    {"name": "Adithya S. Pr", "team": "Arjuna"},
    {"name": "Shaurya Pr", "team": "Arjuna"},
    {"name": "Asmit Pr", "team": "Arjuna"},
    {"name": "Pranav I. Pr", "team": "Arjuna"},
    {"name": "Manan Pr", "team": "Arjuna"},
    {"name": "Mahesh Pr", "team": "Arjuna"},
    {"name": "Sanket Pr", "team": "Arjuna"},
    {"name": "Pranav B. Pr", "team": "Arjuna"},
    {"name": "Rushikesh Pr", "team": "Arjuna"},
    {"name": "Sumit Pr", "team": "Arjuna"},
    # Nakula Team (9)
    {"name": "Shriram Pr", "team": "Nakula"},
    {"name": "Rishit pr", "team": "Nakula"},
    {"name": "Vedant M. Pr", "team": "Nakula"},
    {"name": "Anurag pr", "team": "Nakula"},
    {"name": "Prithviraj Pr", "team": "Nakula"},
    {"name": "Shaunak pr", "team": "Nakula"},
    {"name": "Atul Pr", "team": "Nakula"},
    {"name": "Atharva pr", "team": "Nakula"},
    {"name": "Vipul pr", "team": "Nakula"},
]

def get_all_members():
    return MEMBERS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_current_day')
def get_current_day():
    """Get today's date as day number"""
    from datetime import datetime
    return jsonify({"day": datetime.now().day})

@app.route('/get_all_members')
def api_get_all_members():
    members = get_all_members()
    members_with_index = [{**m, "index": i} for i, m in enumerate(members)]
    return jsonify(members_with_index)

@app.route('/update_attendance', methods=['POST'])
def update_attendance():
    try:
        data = request.json
        day = data['day']
        updates = data['updates']
        all_members = get_all_members()
        
        # Group by team
        team_updates = {}
        for update in updates:
            member = all_members[update['person_idx']]
            team = member['team']
            if team not in team_updates:
                team_updates[team] = []
            team_updates[team].append({**update, 'member': member})
        
        # Parallel processing for each team
        def update_team(team, team_update_list):
            try:
                sheet = spreadsheet.worksheet(team)
                team_members = [m for m in all_members if m['team'] == team]
                batch_data = []
                
                for update in team_update_list:
                    member = update['member']
                    team_position = next(i for i, m in enumerate(team_members) if m['name'] == member['name'])
                    field = update['field']
                    value = update['value']
                    row = 7 + day
                    base_col = 4 + (team_position * 5)
                    
                    col_map = {'sa': 0, 'sb': 1, 'ma': 2, 'in_dk': 3, 'comment': 4}
                    if field in col_map:
                        col = base_col + col_map[field]
                        col_letter = ''
                        temp = col
                        while temp >= 0:
                            col_letter = chr(65 + (temp % 26)) + col_letter
                            temp = temp // 26 - 1
                        batch_data.append({'range': f'{col_letter}{row}', 'values': [[str(value)]]})
                
                if batch_data:
                    sheet.batch_update(batch_data)
            except Exception as e:
                print(f"Error updating {team}: {e}")
        
        # Execute updates in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(update_team, team, updates) for team, updates in team_updates.items()]
            for future in futures:
                future.result()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
