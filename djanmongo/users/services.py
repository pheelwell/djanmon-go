import os
import traceback
import google.generativeai as genai
import pixellab
from django.conf import settings
from typing import List
from .models import User # Import User model
from game.models import Attack # Import Attack model

# --- LLM Prompt Generation ---

def construct_profile_pic_prompt_for_llm(username: str, selected_attacks: List[Attack] = None) -> str:
    """
    Constructs the prompt for the LLM to generate a profile picture description.
    (Same logic as before, just moved here)
    """
    print(f"[Service] Constructing profile pic prompt for user: '{username}'")
    attacks_section = ""
    if selected_attacks:
        attack_details = []
        for attack in selected_attacks:
            attack_details.append(
                f"- Name: {attack.name} ({attack.emoji}), Description: {attack.description}"
            )
        attacks_section = (
            "\\n\\n## User's Selected Attacks (for character inspiration):\\n"
            + "\\n".join(attack_details)
        )

    prompt = f"""
Generate a short, evocative text description suitable for generating a 64x64 pixel art profile picture for a character in a turn-based RPG.

Character Name: {username}
{attacks_section}

## Style Guidelines:
- **Subject:** Focus on a character portrait (head and shoulders or full small character).
- **Theme:** The description should capture the essence of the character based on their name and potentially their selected attacks (if provided).
- **Avoid:** Text, words, complex backgrounds (keep it simple, maybe a plain color or gradient).
- **Conciseness:** The output description should be brief (1-3 sentences, ideally under 30 words).
- **literal** be literal with the description and add something from every attack if possible

## Example Descriptions:
- "A stoic warrior, scarred face, gleaming steel helmet looking"
- "mischievous rogue grinning from beneath a dark hood, holding a dagger, retro"
- "wise old mage with a long white beard and a pointed hat, casting a small spell, clown"
- "cute, fluffy dragon hatchling with big eyes, holding knife, fast, acid"
- "armored knight with a glowing blue sword"

## Task:
Based on  {f'the attacks:{attacks_section}' if attacks_section else 'create a compelling character concept'}, generate ONE suitable description for their pixel art profile picture. Output ONLY the description text.
"""
    print(f"[Service] LLM prompt: '{prompt}'")
    return prompt

def call_llm_for_profile_prompt(llm_input_prompt: str) -> str | None:
    """
    Calls the configured LLM API (e.g., Gemini) to generate the profile picture prompt.
    Returns the cleaned prompt string or None on error.
    (Same logic as before, just moved here)
    """
    try:
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        except AttributeError:
            print("[Service Error] GEMINI_API_KEY not found in Django settings.")
            return None

        model_name = getattr(settings, 'GEMINI_PROFILE_PROMPT_MODEL', 'gemini-2.0-flash') # Default if setting is missing
        print(f"[Service] Using Gemini model for profile prompt: {model_name}") # Added print
        model = genai.GenerativeModel(model_name) # Use configured model name
        safety_settings = {} # Add safety settings if needed
        response = model.generate_content(llm_input_prompt, safety_settings=safety_settings)
        llm_response_text = response.text.strip()

        if not llm_response_text or len(llm_response_text) > 200:
            print(f"[Service Warning] LLM prompt generation returned invalid text: {llm_response_text}")
            return "Generic pixel art character portrait"

        print(f"[Service] LLM generated profile prompt: '{llm_response_text}'")
        return llm_response_text

    except genai.types.generation_types.BlockedPromptException as bpe:
        print(f"[Service Error] LLM profile prompt generation blocked: {bpe}")
        return "Safe default pixel art character portrait"
    except Exception as e:
        print(f"[Service Error] Unexpected error during LLM call for profile prompt: {e}")
        traceback.print_exc()
        return None

# --- Pixel Lab Image Generation ---

def generate_profile_image_with_pixellab(prompt: str, width: int = 32, height: int = 32) -> str | None:
    """
    Generates an image using Pixel Lab's Pixflux endpoint and returns the base64 encoded data.

    Args:
        prompt: The text prompt to describe the desired image.
        width: The desired width of the image (default 64).
        height: The desired height of the image (default 64).

    Returns:
        The base64 encoded string of the generated image, or None if an error occurred.
    """
    print(f"[Service] Attempting Pixel Lab image generation with prompt: '{prompt}'")
    try:
        secret = getattr(settings, 'PIXELLAB_SECRET', os.environ.get('PIXELLAB_SECRET'))
        if not secret:
            print("[Service Error] PIXELLAB_SECRET not found.")
            return None

        client = pixellab.Client(secret=secret)
        response = client.generate_image_pixflux(
            description=prompt,
            image_size={"width": width, "height": height},
        )

        # Check response structure for base64 data
        base64_data = None
        if response and hasattr(response, 'image') and hasattr(response.image, 'base64'):
            base64_data = response.image.base64
        elif response and hasattr(response, 'images') and response.images and len(response.images) > 0 and hasattr(response.images[0], 'base64'):
            base64_data = response.images[0].base64
        
        if base64_data:
             print(f"[Service] Pixel Lab image generated (base64 length: {len(base64_data)})")
             return base64_data
        else:
            # Log the actual response structure if base64 isn't found
            print(f"[Service Error] Pixel Lab response did not contain base64 data. Response: {response}")
            return None

    except Exception as e:
        print(f"[Service Error] Pixel Lab API call failed: {e}")
        traceback.print_exc()
        return None 