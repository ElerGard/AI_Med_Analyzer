import json


def process_node(node):
    result = {}

    if 'meta' in node and 'Группа факторов' in node['meta']:
        group_name = node['name']
        facts = []

        if 'successors' in node and node['successors']:
            for successor in node['successors']:
                if 'meta' in successor and 'Факт' in successor['meta']:
                    # if successor['name'] == 'Отягощенная наследственность':
                    #     print(successor['name'])
                    fact_name = successor['name']
                    characteristics = []

                    if 'successors' in successor and successor['successors']:
                        if successor['successors'][0].get('meta') == 'Составные значения':
                            comp_values = successor['successors'][0]
                            if 'successors' in comp_values:
                                for char_node in comp_values['successors']:
                                    process_characteristic(char_node, characteristics)

                        elif any('Характеристика' in n.get('meta', '') for n in successor['successors']):
                            for char_node in successor['successors']:
                                process_characteristic(char_node, characteristics)

                        else:
                            char_data = {'Качественные значения': [], 'Числовые значения': []}

                            for value_node in successor['successors']:
                                if value_node.get('meta') == 'Качественные значения':
                                    if 'successors' in value_node:
                                        for qual_node in value_node['successors']:
                                            if 'name' in qual_node:
                                                char_data['Качественные значения'].append(qual_node['name'])
                                elif value_node.get('meta') == 'Числовые значения':
                                    if 'successors' in value_node:
                                        for num_node in value_node['successors']:
                                            if 'value' in num_node and isinstance(num_node['value'], (int, float)):
                                                char_data['Числовые значения'].append(num_node['value'])
                                elif 'name' in value_node and value_node.get('type') != 'НЕТЕРМИНАЛ':
                                    char_data['Качественные значения'].append(value_node['name'])
                                elif 'value' in value_node and isinstance(value_node['value'], (int, float)):
                                    char_data['Числовые значения'].append(value_node['value'])

                            characteristics.append(char_data)

                    facts.append({
                        fact_name: characteristics if characteristics else [
                            {'Качественные значения': [], 'Числовые значения': []}]
                    })

        if facts:
            result[group_name] = facts

    return result


def process_characteristic(char_node, characteristics):
    if ('meta' in char_node and ('Характеристика' in char_node['meta'] or
                                 'Качественные значения' in char_node['meta'] or
                                 'Числовые значения' in char_node['meta'])) or \
            ('name' in char_node and char_node.get('type') != 'НЕТЕРМИНАЛ'):

        char_name = char_node.get('name', 'Значения')
        char_data = {'Качественные значения': [], 'Числовые значения': []}

        if 'successors' in char_node:
            for value_node in char_node['successors']:
                if value_node.get('meta') == 'Качественные значения':
                    if 'successors' in value_node:
                        for qual_node in value_node['successors']:
                            if 'name' in qual_node:
                                char_data['Качественные значения'].append(qual_node['name'])

                elif value_node.get('meta') == 'Числовые значения':
                    if 'successors' in value_node:
                        for num_node in value_node['successors']:
                            if 'value' in num_node and isinstance(num_node['value'], (int, float)):
                                char_data['Числовые значения'].append(num_node['value'])

                elif 'name' in value_node and value_node.get('type') != 'НЕТЕРМИНАЛ':
                    char_data['Качественные значения'].append(value_node['name'])
                elif 'value' in value_node and isinstance(value_node['value'], (int, float)):
                    char_data['Числовые значения'].append(value_node['value'])

        characteristics.append({
            char_name: char_data
        })


def search_patient_card(input_json):
    if isinstance(input_json, dict):
        if input_json.get('name') == 'Карта пациента':
            return input_json
        if 'successors' in input_json:
            for node in input_json['successors']:
                result = search_patient_card(node)
                if result:
                    return result
    elif isinstance(input_json, list):
        for item in input_json:
            result = search_patient_card(item)
            if result:
                return result
    return None


def process_json(input_json):
    output = []
    patient_card = search_patient_card(input_json)

    if patient_card and 'successors' in patient_card:
        for node in patient_card['successors']:
            processed = process_node(node)
            if processed:
                output.append(processed)

    return output


with open('data/База медицинской терминологии и наблюдений 2020 - Практика 2025.universal.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

result = process_json(data)

with open('data/template.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Обработка завершена. Результат сохранен в data/template.json")