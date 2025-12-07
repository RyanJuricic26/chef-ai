# catalog_utils.py
import re
import json
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup


def fetch_html_content(url: str, timeout: int = 30, user_agent: str = None) -> str:
    """
    Fetch HTML content from a URL with proper encoding handling.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        user_agent: User agent string
        
    Returns:
        HTML content as string with proper encoding
        
    Raises:
        Exception: If request fails
    """
    import requests
    
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent
    
    try:
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        
        # Ensure proper encoding - try to detect from response
        if response.encoding is None or response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
            # Try to detect encoding from content
            response.encoding = response.apparent_encoding or 'utf-8'
        
        return response.text
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch webpage: {str(e)}")


def strip_html_tags(text: str) -> str:
    """
    Strip HTML tags from text and decode HTML entities.
    
    Args:
        text: Text that may contain HTML tags
        
    Returns:
        Clean text without HTML tags
    """
    if not text:
        return ""
    
    # Parse with BeautifulSoup to strip tags and decode entities
    soup = BeautifulSoup(text, 'html.parser')
    # Get text and decode HTML entities
    cleaned = soup.get_text(separator=' ', strip=True)
    
    # Additional cleanup: remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    return cleaned


def parse_json_ld_from_html(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON-LD Recipe schema from HTML content.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Parsed JSON-LD Recipe data or None if not found
    """
    # Use lxml parser if available for better encoding handling, fallback to html.parser
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except:
        soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all script tags with type="application/ld+json"
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    
    for script in json_ld_scripts:
        try:
            script_content = script.string
            if not script_content:
                continue
            
            # Parse JSON - handle encoding issues
            data = json.loads(script_content)
            
            # Handle both single objects and arrays
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'Recipe':
                        return item
            elif isinstance(data, dict):
                if data.get('@type') == 'Recipe':
                    return data
                # Check for @graph array
                if '@graph' in data:
                    for item in data['@graph']:
                        if isinstance(item, dict) and item.get('@type') == 'Recipe':
                            return item
        except (json.JSONDecodeError, AttributeError):
            continue
    
    return None


def parse_iso8601_duration(duration_str: str) -> int:
    """
    Convert ISO 8601 duration to minutes.
    
    Examples:
        "PT30M" -> 30
        "PT1H30M" -> 90
        "PT2H" -> 120
        
    Args:
        duration_str: ISO 8601 duration string
        
    Returns:
        Duration in minutes
    """
    if not duration_str or not duration_str.startswith('PT'):
        return 0
    
    duration_str = duration_str[2:]  # Remove 'PT' prefix
    
    hours = 0
    minutes = 0
    
    # Extract hours
    hour_match = re.search(r'(\d+)H', duration_str)
    if hour_match:
        hours = int(hour_match.group(1))
    
    # Extract minutes
    minute_match = re.search(r'(\d+)M', duration_str)
    if minute_match:
        minutes = int(minute_match.group(1))
    
    return hours * 60 + minutes


def extract_recipe_from_json_ld(json_ld_data: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Extract recipe data from JSON-LD Recipe schema.
    
    Args:
        json_ld_data: Parsed JSON-LD Recipe object
        url: Source URL
        
    Returns:
        Recipe data dictionary
    """
    # Clean name and description
    name = json_ld_data.get("name", "")
    if name:
        name = strip_html_tags(name)
    
    description = json_ld_data.get("description", "")
    if description:
        description = strip_html_tags(description)
    
    recipe_data = {
        "name": name,
        "description": description,
        "url": url,
        "prep_time": 0,
        "cook_time": 0,
        "servings": None,
        "difficulty": None,
        "cuisine_type": json_ld_data.get("recipeCuisine", ""),
        "instructions": "",
        "ingredients": []
    }
    
    # Parse prep time
    prep_time = json_ld_data.get("prepTime", "")
    if prep_time:
        recipe_data["prep_time"] = parse_iso8601_duration(prep_time)
    
    # Parse cook time
    cook_time = json_ld_data.get("cookTime", "")
    if cook_time:
        recipe_data["cook_time"] = parse_iso8601_duration(cook_time)
    
    # Parse servings
    recipe_yield = json_ld_data.get("recipeYield")
    if recipe_yield:
        if isinstance(recipe_yield, (int, float)):
            recipe_data["servings"] = int(recipe_yield)
        elif isinstance(recipe_yield, str):
            # Try to extract number from string like "4 servings"
            numbers = re.findall(r'\d+', recipe_yield)
            if numbers:
                recipe_data["servings"] = int(numbers[0])
    
    # Parse instructions
    instructions = json_ld_data.get("recipeInstructions", [])
    if isinstance(instructions, str):
        # Clean HTML tags and format
        cleaned_instructions = strip_html_tags(instructions)
        # Format with proper line breaks - split by periods followed by space or newline
        formatted = format_instructions(cleaned_instructions)
        # Ensure we don't lose the instructions
        recipe_data["instructions"] = formatted if formatted else cleaned_instructions
    elif isinstance(instructions, list):
        # Handle both text and HowToStep objects
        instruction_parts = []
        for step in instructions:
            if isinstance(step, dict):
                text = step.get("text", step.get("@type", ""))
                if text:
                    # Clean HTML tags from each step
                    cleaned_text = strip_html_tags(text)
                    if cleaned_text:
                        instruction_parts.append(cleaned_text)
            elif isinstance(step, str):
                # Clean HTML tags
                cleaned_text = strip_html_tags(step)
                if cleaned_text:
                    instruction_parts.append(cleaned_text)
        # Join with line breaks and format
        if instruction_parts:
            combined = "\n".join(instruction_parts)
            formatted = format_instructions(combined)
            # Ensure we don't lose the instructions
            recipe_data["instructions"] = formatted if formatted else combined
        else:
            recipe_data["instructions"] = ""
    
    # Parse ingredients
    recipe_ingredients = json_ld_data.get("recipeIngredient", [])
    if not recipe_ingredients:
        recipe_ingredients = json_ld_data.get("ingredients", [])
    
    for ing_str in recipe_ingredients:
        if isinstance(ing_str, str):
            # Clean HTML tags from ingredient string first
            cleaned_ing = strip_html_tags(ing_str)
            parsed_ing = parse_ingredient_string(cleaned_ing)
            if parsed_ing:
                recipe_data["ingredients"].append(parsed_ing)
    
    return recipe_data


def format_instructions(instructions: str) -> str:
    """
    Format instructions with proper line breaks and structure.
    Splits by numbered steps, section headers, or sentence endings.
    
    Args:
        instructions: Raw instructions text
        
    Returns:
        Formatted instructions with proper line breaks and structure
    """
    if not instructions:
        return ""
    
    import re
    
    # Clean the instructions first
    instructions = instructions.strip()
    if not instructions:
        return ""
    
    # First, try to split by numbered steps (1., 2., etc. or 1), 2), etc.)
    # Look for patterns like "1. ", "2. ", "1) ", "2) "
    numbered_pattern = r'(\d+[\.\)]\s+)'
    parts = re.split(numbered_pattern, instructions)
    
    if len(parts) > 1:
        # We have numbered steps - parts will be: [text, separator, text, separator, ...]
        formatted = []
        current_step = ""
        
        for i, part in enumerate(parts):
            if re.match(r'^\d+[\.\)]\s+$', part):
                # This is a separator (e.g., "1. " or "2) ")
                if current_step:
                    formatted.append(current_step.strip())
                current_step = part
            else:
                # This is text content
                if current_step:
                    current_step += part
                else:
                    # First part might not have a separator
                    if part.strip():
                        formatted.append(part.strip())
        
        # Add the last step
        if current_step:
            formatted.append(current_step.strip())
        
        if formatted:
            return "\n\n".join(formatted)  # Double line break for numbered steps
    
    # If no numbered steps, look for section headers (e.g., "To make...", "To assemble...")
    # Common patterns: "To [verb]", "For [noun]", "In [location]", imperative verbs at start
    section_pattern = r'(?=\b(?:To|For|In|Place|Add|Mix|Combine|Heat|Cook|Bake|Roast|Fry|Simmer|Boil|Preheat|Season|Garnish|Serve|Assemble|Layer|Divide|Scatter|Drizzle|Tuck|Warm|Stir|Toss|Spread|Drain|Cut|Slice|Chop|Peel|Remove)\b)'
    sections = re.split(section_pattern, instructions, flags=re.IGNORECASE)
    
    if len(sections) > 1:
        # We have section headers
        formatted = []
        for section in sections:
            section = section.strip()
            if section:
                # Further split by sentence endings within each section
                sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', section)
                if len(sentences) > 1:
                    # Join sentences in section with single line break
                    formatted.append("\n".join(s.strip() for s in sentences if s.strip()))
                else:
                    formatted.append(section)
        
        if formatted:
            return "\n\n".join(formatted)  # Double line break between sections
    
    # If no sections, try splitting by sentence endings with better formatting
    # Split by periods/exclamation/question marks followed by space and capital letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', instructions)
    
    if len(sentences) > 1:
        # Group sentences into logical paragraphs (2-3 sentences per paragraph)
        formatted = []
        current_para = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            current_para.append(sentence)
            
            # Start a new paragraph every 2-3 sentences, or if sentence is long
            if len(current_para) >= 2 or len(sentence) > 150:
                formatted.append(" ".join(current_para))
                current_para = []
        
        # Add remaining sentences
        if current_para:
            formatted.append(" ".join(current_para))
        
        if formatted:
            return "\n\n".join(formatted)  # Double line break between paragraphs
    
    # If all else fails, return as-is but ensure it's clean
    # This ensures we never return empty string if input had content
    return instructions.strip() if instructions.strip() else ""


def parse_ingredient_string(ingredient_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse an ingredient string into structured data.
    Strips HTML tags and handles special characters.
    
    Examples:
        "2 cups flour" -> {"name": "flour", "quantity": "2", "unit": "cups", "category": "grain"}
        "1 tsp salt" -> {"name": "salt", "quantity": "1", "unit": "tsp", "category": "spice"}
        
    Args:
        ingredient_str: Raw ingredient string (may contain HTML)
        
    Returns:
        Ingredient dictionary or None if parsing fails
    """
    if not ingredient_str or not ingredient_str.strip():
        return None
    
    # Strip HTML tags if present
    ingredient_str = strip_html_tags(ingredient_str)
    
    # Common units
    units = [
        "cup", "cups", "c", "tablespoon", "tablespoons", "tbsp", "tbsp.", "T",
        "teaspoon", "teaspoons", "tsp", "tsp.", "t",
        "pound", "pounds", "lb", "lbs", "lb.", "lbs.",
        "ounce", "ounces", "oz", "oz.",
        "gram", "grams", "g", "g.",
        "kilogram", "kilograms", "kg", "kg.",
        "milliliter", "milliliters", "ml", "ml.",
        "liter", "liters", "l", "l.",
        "piece", "pieces", "pc", "pcs",
        "clove", "cloves",
        "bunch", "bunches",
        "head", "heads",
        "can", "cans",
        "package", "packages", "pkg", "pkgs"
    ]
    
    # Pattern to match quantity and unit
    # Matches: "2 cups", "1/2 tsp", "1.5 tbsp", etc.
    pattern = r'^([\d\s/\.]+)\s*([a-zA-Z]+\.?)\s+(.+)$'
    match = re.match(pattern, ingredient_str.strip(), re.IGNORECASE)
    
    if match:
        quantity = match.group(1).strip()
        unit = match.group(2).strip().lower()
        name = match.group(3).strip()
        
        # Normalize unit
        unit_lower = unit.rstrip('.')
        if unit_lower not in [u.rstrip('.') for u in units]:
            # Unit not recognized, might be part of name
            name = f"{unit} {name}"
            unit = ""
            quantity = match.group(1).strip()
    else:
        # Try to extract just quantity
        quantity_match = re.match(r'^([\d\s/\.]+)\s+(.+)$', ingredient_str.strip())
        if quantity_match:
            quantity = quantity_match.group(1).strip()
            name = quantity_match.group(2).strip()
            unit = ""
        else:
            # No quantity found
            quantity = ""
            unit = ""
            name = ingredient_str.strip()
    
    # Categorize ingredient
    category = categorize_ingredient(name)
    
    return {
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "category": category
    }


def categorize_ingredient(ingredient_name: str) -> str:
    """
    Categorize an ingredient based on its name.
    
    Args:
        ingredient_name: Name of the ingredient
        
    Returns:
        Category string (meat, vegetable, dairy, spice, grain, etc.)
    """
    name_lower = ingredient_name.lower()
    
    # Meat categories
    meat_keywords = ["chicken", "beef", "pork", "lamb", "turkey", "duck", "bacon", "sausage", 
                     "ham", "prosciutto", "pancetta", "steak", "ground", "mince"]
    if any(keyword in name_lower for keyword in meat_keywords):
        return "meat"
    
    # Seafood
    seafood_keywords = ["fish", "salmon", "tuna", "shrimp", "prawn", "crab", "lobster", 
                        "mussel", "clam", "oyster", "squid", "octopus", "cod", "tilapia"]
    if any(keyword in name_lower for keyword in seafood_keywords):
        return "seafood"
    
    # Dairy
    dairy_keywords = ["milk", "cheese", "butter", "cream", "yogurt", "yoghurt", "sour cream",
                      "buttermilk", "mascarpone", "ricotta", "mozzarella", "parmesan"]
    if any(keyword in name_lower for keyword in dairy_keywords):
        return "dairy"
    
    # Vegetables
    vegetable_keywords = ["onion", "garlic", "tomato", "pepper", "carrot", "celery", "potato",
                          "lettuce", "spinach", "broccoli", "cauliflower", "cabbage", "mushroom",
                          "zucchini", "eggplant", "cucumber", "peas", "beans", "corn"]
    if any(keyword in name_lower for keyword in vegetable_keywords):
        return "vegetable"
    
    # Spices and herbs
    spice_keywords = ["salt", "pepper", "paprika", "cumin", "coriander", "turmeric", "cinnamon",
                      "nutmeg", "ginger", "garlic", "basil", "oregano", "thyme", "rosemary",
                      "parsley", "cilantro", "chili", "chilli", "curry", "spice"]
    if any(keyword in name_lower for keyword in spice_keywords):
        return "spice"
    
    # Grains and starches
    grain_keywords = ["flour", "rice", "pasta", "noodle", "bread", "quinoa", "barley", "oats",
                      "wheat", "cornmeal", "polenta", "couscous"]
    if any(keyword in name_lower for keyword in grain_keywords):
        return "grain"
    
    # Fruits
    fruit_keywords = ["apple", "banana", "orange", "lemon", "lime", "berry", "strawberry",
                      "blueberry", "raspberry", "mango", "pineapple", "peach", "pear"]
    if any(keyword in name_lower for keyword in fruit_keywords):
        return "fruit"
    
    # Nuts and seeds
    nut_keywords = ["almond", "walnut", "pecan", "peanut", "cashew", "pistachio", "hazelnut",
                    "sesame", "sunflower", "pumpkin", "seed"]
    if any(keyword in name_lower for keyword in nut_keywords):
        return "nut"
    
    # Oils and fats
    oil_keywords = ["oil", "olive oil", "vegetable oil", "canola", "butter", "lard", "shortening"]
    if any(keyword in name_lower for keyword in oil_keywords):
        return "oil"
    
    # Default category
    return "other"


def clean_html_for_llm(html_content: str) -> str:
    """
    Clean HTML content for LLM processing by removing scripts, styles, and unnecessary tags.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "meta", "link"]):
        script.decompose()
    
    # Get text content
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    # Limit length to avoid token limits (keep first 10000 characters)
    if len(text) > 10000:
        text = text[:10000] + "..."
    
    return text


def infer_difficulty(instructions: str, prep_time: int = 0, cook_time: int = 0) -> str:
    """
    Infer recipe difficulty based on instructions and time.
    
    Args:
        instructions: Recipe instructions text
        prep_time: Preparation time in minutes
        cook_time: Cooking time in minutes
        
    Returns:
        Difficulty level: "easy", "medium", or "hard"
    """
    total_time = prep_time + cook_time
    
    # Count instruction steps
    steps = [s.strip() for s in instructions.split('\n') if s.strip()]
    num_steps = len(steps)
    
    # Simple heuristics
    if total_time <= 30 and num_steps <= 5:
        return "easy"
    elif total_time <= 60 and num_steps <= 10:
        return "medium"
    else:
        return "hard"
