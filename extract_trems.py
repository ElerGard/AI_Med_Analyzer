import json

def extract_terms(data, path='', result=None):
    if result is None:
        result = {}

    if data['type'] != 'КОРЕНЬ':
        current_path = f"{path}/{data['name']}" if path else data['name']
    else:
        current_path = ''

    if data['type'] == 'НЕТЕРМИНАЛ':
        path_str = f"{current_path};"
        if path_str not in result.values():
            result[current_path] = path_str

    if 'successors' in data and data['successors']:
        for item in data['successors']:
            if item['type'] == 'НЕТЕРМИНАЛ':
                extract_terms(item, current_path, result)
            elif item['type'] == 'ТЕРМИНАЛ-ЗНАЧЕНИЕ':
                term_path = f"{current_path}/{item['value']};"
                if term_path not in result.values():
                    result[item['value']] = term_path

    return result

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Ошибка: Файл {file_path} не найден!")
        return None
    except json.JSONDecodeError:
        print(f"Ошибка: Файл {file_path} содержит некорректный JSON!")
        return None

file_path = "data/База медицинской терминологии и наблюдений 2020 - Практика 2025.universal.json"
json_data = load_json_file(file_path)

if json_data:
    terms_dict = extract_terms(json_data)
    with open('data/term.txt', 'w', encoding='utf-8') as file:
        for path in sorted(terms_dict.values()):
            file.write(path + '\n')
    print(f"Сгенерировано {len(terms_dict)} уникальных путей.")