import requests
import json
import time
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse # To get the API endpoint URL
from django.conf import settings
from users.models import User # To get an authenticated user

# --- Configuration ---
NUMBER_OF_TEST_ATTACKS = 10
BASE_API_URL = "http://127.0.0.1:8000" # Adjust if your dev server runs elsewhere
TEST_USERNAME = "q" # CHANGE THIS to a username that exists in your DB
TEST_PASSWORD = "1" # CHANGE THIS to the password for the user

# Simple themes/prompts for testing
TEST_PROMPTS = [
    ("Overpowered", "instant winning attacks, high damage"),
    ("Shadow", "Dark energy attacks, maybe life drain"),
    ("Anoying", "maximize anoying effects that drag along and suck fun"),
    ("Toxic", "Poison/acid attacks, damage over time"),
    ("Holy", "Light-based attacks, healing or smiting"),
    ("Electric", "Lightning attacks, high speed/paralysis"),
    ("Earth", "Rock/ground attacks, high defense/impact"),
    ("Wind", "Air attacks, speed manipulation"),
    ("Mental", "Psychic attacks, status effects"),
    ("Chaos", "Unpredictable, random effects"),
]

class Command(BaseCommand):
    help = 'Tests the attack generation API endpoint by creating multiple attack sets.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Starting Attack Generation Test ---'))

        # --- 1. Authenticate Test User ---
        self.stdout.write(f"Attempting to authenticate as user: {TEST_USERNAME}")
        login_url = f"{BASE_API_URL}/api/users/login/"
        try:
            response = requests.post(login_url, data={'username': TEST_USERNAME, 'password': TEST_PASSWORD})
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            tokens = response.json()
            access_token = tokens.get('access')
            if not access_token:
                raise CommandError("Login successful, but no access token received.")
            self.stdout.write(self.style.SUCCESS("Authentication successful."))
        except requests.exceptions.RequestException as e:
            raise CommandError(f"Authentication failed: {e}. Response: {e.response.text if e.response else 'No Response'}")
        except Exception as e:
            raise CommandError(f"An unexpected error occurred during authentication: {e}")

        # --- 2. Prepare API Client (Session with Auth Header) ---
        api_session = requests.Session()
        api_session.headers.update({'Authorization': f'Bearer {access_token}'})
        generate_url = f"{BASE_API_URL}{reverse('attack_generate')}" # Use reverse lookup

        self.stdout.write(f"API Endpoint: {generate_url}")

        # --- 3. Loop and Generate Attacks ---
        successful_generations = 0
        failed_generations = 0

        for i in range(NUMBER_OF_TEST_ATTACKS):
            theme, prompt_desc = TEST_PROMPTS[i % len(TEST_PROMPTS)] # Cycle through prompts
            attack_set_name = f"{theme} Test Set {i+1}"
            prompt_text = f"{prompt_desc} - Test {i+1}"

            self.stdout.write(f"\n--- Generating Attack Set {i+1}/{NUMBER_OF_TEST_ATTACKS} ---")
            self.stdout.write(f"  Name: {attack_set_name}")
            self.stdout.write(f"  Prompt: {prompt_text}")

            attack_ids = []

            try:
                # Remove set_name generation
                payload_dict = {"concept": prompt_text} # Pass concept directly
                
                # Use the APIClient instance (client.post)
                response = api_session.post(generate_url, json=payload_dict)
                response.raise_for_status() # Check for HTTP errors

                result = response.json()
                self.stdout.write(self.style.SUCCESS(f"  Success: {result.get('message', 'OK')}"))

                # Print generated attack details
                if result.get('attacks'):
                    self.stdout.write("    --- Generated Attack Details ---")
                    for attack in result['attacks']:
                        self.stdout.write(f"      Attack: {attack.get('name', 'N/A')}")
                        self.stdout.write(f"        Desc: {attack.get('description', 'N/A')}")
                        self.stdout.write(f"        Emoji: {attack.get('emoji', 'N/A')}")
                        self.stdout.write(f"        Cost: {attack.get('momentum_cost', 'N/A')}")
                        script_data = attack.get('script', {})
                        self.stdout.write(f"        Trigger: {script_data.get('trigger_type', 'N/A')}")
                        lua_code = script_data.get('lua_code', 'N/A')
                        # Indent Lua code for readability
                        indented_lua = "\n".join([f"          {line}" for line in lua_code.splitlines()])
                        self.stdout.write(f"        Lua Code:\n{indented_lua}")
                        self.stdout.write("      -------------------------------") # Separator

                successful_generations += 1

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"  Failed: HTTP Error {e.response.status_code if e.response else 'N/A'}"))
                try:
                     error_data = e.response.json()
                     self.stdout.write(self.style.ERROR(f"    Error Detail: {error_data.get('error', json.dumps(error_data))}"))
                except (json.JSONDecodeError, AttributeError):
                     self.stdout.write(self.style.ERROR(f"    Response Text: {e.response.text if e.response else 'No Response'}"))
                failed_generations += 1
            except json.JSONDecodeError as e:
                 self.stdout.write(self.style.ERROR(f"  Failed: Could not decode JSON response."))
                 self.stdout.write(self.style.ERROR(f"    Raw Response: {response.text}"))
                 failed_generations +=1
            except Exception as e:
                 self.stdout.write(self.style.ERROR(f"  Failed: An unexpected error occurred: {e}"))
                 failed_generations += 1

            # Add a small delay to avoid overwhelming the API/LLM (optional)
            time.sleep(1)

        # --- 4. Print Summary ---
        self.stdout.write("\n" + "="*40)
        self.stdout.write(self.style.SUCCESS("--- Test Complete ---"))
        self.stdout.write(f"Successful Generations: {successful_generations}")
        self.stdout.write(f"Failed Generations:     {failed_generations}")
        self.stdout.write("="*40) 