import re

def camel_to_snake(str):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', str).lower()

def snake_to_camel(str):
    return str.title().replace("_", "")