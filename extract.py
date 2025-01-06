import fireworks.client
import base64
from pathlib import Path
import json

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def clean_json_response(response):
    start = response.find('{')
    end = response.rfind('}')
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in response")
    
    json_str = response[start:end + 1]
    
    json_str = json_str.replace('```json', '').replace('```', '')
    json_str = json_str.replace('\n\n', '\n')
    json_str = '\n'.join(line.strip() for line in json_str.splitlines())  # Clean each line
    
    return json_str

def process_image(image_path):
    image_base64 = encode_image(image_path)
    
    # First, identify the document type
    type_response = fireworks.client.ChatCompletion.create(
        model="accounts/fireworks/models/phi-3-vision-128k-instruct",
        messages=[{
            "role": "user",
            "content": [{
                "type": "text",
                "text": "What type of document is this? Please respond with only: 'DRIVERS_LICENSE' or 'PASSPORT' or 'OTHER'",
            }, {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                },
            }],
        }],
    )
    doc_type = type_response.choices[0].message.content.strip()

    # Based on document type, extract specific information
    if doc_type == "DRIVERS_LICENSE":
        prompt = """
        Extract the following information from this driver's license and return ONLY a JSON object with no additional text or markdown:
        - License Number
        - Expiration Date
        - Class
        - Last Name
        - First Name
        - Date of Birth
        - Sex
        
        Use this exact format:
        {
            "license_number": "",
            "expiration_date": "",
            "class": "",
            "last_name": "",
            "first_name": "",
            "date_of_birth": "",
            "sex": ""
        }
        """
    elif doc_type == "PASSPORT":
        prompt = """
        Extract the following information from this passport and return ONLY a JSON object with no additional text or markdown:
        - Passport Number
        - Country Code
        - Last Name
        - First Name
        - Nationality
        - Date of Birth
        - Sex
        - Date of Issue
        - Date of Expiry
        
        Use this exact format:
        {
            "passport_number": "",
            "country_code": "",
            "last_name": "",
            "first_name": "",
            "nationality": "",
            "date_of_birth": "",
            "sex": "",
            "date_of_issue": "",
            "date_of_expiry": ""
        }
        """
    else:
        return {"error": "Unsupported document type", "type": doc_type}

    info_response = fireworks.client.ChatCompletion.create(
        model="accounts/fireworks/models/phi-3-vision-128k-instruct",
        messages=[{
            "role": "user",
            "content": [{
                "type": "text",
                "text": prompt,
            }, {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                },
            }],
        }],
    )
    
    try:
        cleaned_response = clean_json_response(info_response.choices[0].message.content)
        extracted_info = json.loads(cleaned_response)
        extracted_info["document_type"] = doc_type
        return extracted_info
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "error": f"Failed to parse response: {str(e)}", 
            "raw_response": info_response.choices[0].message.content,
            "document_type": doc_type
        }

fireworks.client.api_key = "fw_3ZccQcN3o5XczFVAUTaJLwLY"

data_dir = Path("data")
supported_formats = ('.png', '.jpg', '.jpeg')

results = {}
for image_file in data_dir.glob("*"):
    if image_file.suffix.lower() in supported_formats:
        print(f"\nProcessing {image_file.name}...")
        try:
            results[image_file.name] = process_image(str(image_file))
        except Exception as e:
            print(f"Error processing {image_file.name}: {e}")
            results[image_file.name] = {"error": str(e)}

for image_name, data in results.items():
    print(f"\n=== {image_name} ===")
    print(json.dumps(data, indent=2))

with open('extracted_data.json', 'w') as f:
    json.dump(results, f, indent=2)
