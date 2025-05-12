import json
import uuid
from datetime import datetime
import re
from config import IACP_Settings
with open('data/term.txt', 'r', encoding='utf-8') as f:
    terminology = [line.strip() for line in f.readlines()]


def find_original_path(name, parent_name=None, value=None):
    search_terms = []
    # if name == 'аллергия отсутствует':
    #     print(1)

    if name in ['Качественные значения', 'Числовые значения', 'Составные значения'] and value is None:
        return None

    if value:
        search_terms.append(f"/{value};")
    else:
        search_terms.append(f"/{name};")


    for term in terminology:
        for search_term in search_terms:
            if search_term in term:
                return term
            elif not value:
                match = re.search(rf'^(.*?)/{name};', term)
                if match:
                    result = match.group(1) + f"/{name};"
                    return result
    return None


def generate_id():
    return int(str(uuid.uuid4().int)[:16])


def transform_value(value, parent_name=None, name=None):
    if isinstance(value, (str, int, float)):
        node = {
            "id": generate_id(),
            "value": value,
            "type": "ТЕРМИНАЛ-ЗНАЧЕНИЕ",
            "meta": "значение"
        }

        if isinstance(value, str):
            if value.endswith('.000') and len(value) == 23:
                node["valtype"] = "DATE"
                node["meta"] = "дата"
            else:
                node["valtype"] = "STRING"
        elif isinstance(value, int):
            node["valtype"] = "INTEGER"
        elif isinstance(value, float):
            node["valtype"] = "REAL"

        original = find_original_path(name, parent_name, str(value))
        if original:
            node[
                "original"] = IACP_Settings.TERMS_PATH + original

        return node

    return None


def transform_node(key, value, parent_key=None, is_special_section=False, is_fact=False):
    if key == 'Наличие аллергии':
        print(1)
    if is_special_section or key == 'Качественные значения' or key == 'Числовые значения':
        meta = key
        is_fact = False
    else:
        meta = "Характеристика" if not is_fact else "Факт"
    node = {
        "id": generate_id(),
        "name": key,
        "type": "НЕТЕРМИНАЛ",
        "meta": meta,
        "successors": []
    }

    if is_fact:
        original = find_original_path(key, parent_key)
        if original:
            node[
                "original"] = IACP_Settings.TERMS_PATH + original

    if isinstance(value, dict):
        values_exist = False
        for k, v in value.items():
            if k in ["Качественные значения", "Числовые значения"]:
                if values_exist:
                    break
                values_exist = True
                values_node = {
                    "id": generate_id(),
                    "name": k,
                    "type": "НЕТЕРМИНАЛ",
                    "meta": k,
                    "successors": []
                }

                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, (str, int, float)):
                            term_node = transform_value(item, key, k)
                            if term_node:
                                values_node["successors"].append(term_node)

                node["successors"].append(values_node)
            else:
                if not is_special_section:
                    child_node = transform_node(k, v, key, is_fact=False)
                else:
                    child_node = transform_node(k, v, key, is_fact=True)
                if child_node:
                    node["successors"].append(child_node)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                if "Качественные значения" in item and item['Качественные значения'] != []:
                    item = {"Качественные значения": item['Качественные значения']}
                elif "Числовые значения" in item and item['Числовые значения'] != []:
                    item = {"Числовые значения": item['Числовые значения']}
                for k, v in item.items():
                    if is_fact and isinstance(v, (str, int, float)):
                        qual_node = {
                            "id": generate_id(),
                            "name": "Качественные значения",
                            "type": "НЕТЕРМИНАЛ",
                            "meta": "Качественные значения",
                            "successors": [transform_value(v, key, k)]
                        }
                        node["successors"].append(qual_node)
                    else:
                        if not is_special_section:
                            child_node = transform_node(k, v, key, is_fact=False)
                        else:
                            child_node = transform_node(k, v, key, is_fact=True)
                        node["successors"].append(child_node)
            elif isinstance(item, (str, int, float)):
                if is_fact:
                    qual_node = {
                        "id": generate_id(),
                        "name": "Качественные значения",
                        "type": "НЕТЕРМИНАЛ",
                        "meta": "Качественные значения",
                        "successors": [transform_value(item, parent_key, key)]
                    }
                    node["successors"].append(qual_node)
                else:
                    term_node = transform_value(item, parent_key, key)
                    if term_node:
                        node["successors"].append(term_node)
    elif isinstance(value, (str, int, float)):
        if is_fact:
            qual_node = {
                "id": generate_id(),
                "name": "Качественные значения",
                "type": "НЕТЕРМИНАЛ",
                "meta": "Качественные значения",
                "successors": [transform_value(value, parent_key, key)]
            }
            node["successors"].append(qual_node)
        else:
            term_node = transform_value(value, parent_key, key)
            if term_node:
                node["successors"].append(term_node)

    if is_special_section and not is_fact:
        record_node = {
            "id": generate_id(),
            "name": "1",
            "type": "НЕТЕРМИНАЛ",
            "meta": "Номер записи",
            "successors": [
                {
                    "id": generate_id(),
                    "value": datetime.now().strftime("%d.%m.%Y-%H:%M:%S.000"),
                    "type": "ТЕРМИНАЛ-ЗНАЧЕНИЕ",
                    "valtype": "DATE",
                    "meta": "дата"
                }
            ]
        }

        if node["successors"]:
            record_node["successors"].extend(node["successors"])

        node["successors"] = [record_node]

    return node


def transform_json(input_json, filename):
    special_sections = [
        "Вредные привычки",
        "Аллергологический анамнез",
        "Перенесенные заболевания, травмы, операции",
        "Наследственный анамнез",
        "Сопутствующие и хронические заболевания",
        "Семейный анамнез",
        "Вакцинация",
        "Наличие инвалидности",
        "Акушерский анамнез",
        "Трудовой анамнез"
    ]

    output = {
        "title": IACP_Settings.TITLE,
        "code": "4642140371393939950",
        "path": IACP_Settings.PATH,
        "date": datetime.now().strftime("%d.%m.%Y-%H:%M:%S.%f")[:-3],
        "creation": "29.04.2025-22:11:34.819",
        "owner_id": 751,
        "json_type": "universal",
        "ontology": IACP_Settings.ONTOLOGY_PATH,
        "id": 2793382304808964,
        "name": IACP_Settings.TITLE,
        "type": "КОРЕНЬ",
        "meta": "Онтология электронной медицинской карты V.4 - Практика 2025",
        "successors": [
            {
                "id": 2793382304808968,
                "name": "Врачебные осмотры, консультации, истории болезни",
                "type": "НЕТЕРМИНАЛ",
                "meta": "Врачебные осмотры, консультации, истории болезни",
                "successors": [
                    {
                        "id": 2793382304813388,
                        "name": f"{filename}",
                        "type": "НЕТЕРМИНАЛ",
                        "meta": "История болезни или наблюдений v.4",
                        "successors": [
                            {
                                "id": 2793382304813392,
                                "name": "Паспортная часть",
                                "type": "НЕТЕРМИНАЛ",
                                "meta": "Паспортная часть",
                                "successors": []
                            },
                            {
                                "id": 2793382304813396,
                                "name": "Жалобы",
                                "type": "НЕТЕРМИНАЛ",
                                "meta": "Жалобы",
                                "successors": []
                            },
                            {
                                "id": 2793382304813400,
                                "name": "Объективное состояние",
                                "type": "НЕТЕРМИНАЛ",
                                "meta": "Объективное состояние",
                                "successors": [
                                    {
                                        "id": 2793382304813404,
                                        "name": "Общий осмотр",
                                        "type": "НЕТЕРМИНАЛ",
                                        "meta": "Общий осмотр",
                                        "successors": []
                                    }
                                ]
                            },
                            {
                                "id": 2793382304813408,
                                "name": "Результаты компьютерной постановки диагноза",
                                "type": "НЕТЕРМИНАЛ",
                                "meta": "Результаты компьютерной постановки диагноза",
                                "successors": []
                            },
                            {
                                "id": 2793382304813412,
                                "name": "Результаты компьютерного назначения лечения",
                                "type": "НЕТЕРМИНАЛ",
                                "meta": "Результаты компьютерного назначения лечения",
                                "successors": []
                            },
                            {
                                "id": 2793382304813416,
                                "name": "Анамнез жизни",
                                "type": "НЕТЕРМИНАЛ",
                                "meta": "Анамнез жизни",
                                "successors": []
                            }
                        ]
                    }
                ]
            }
        ]
    }

    anamnez_life = None
    for successor in output["successors"][0]["successors"][0]["successors"]:
        if successor["name"] == "Анамнез жизни":
            anamnez_life = successor
            break

    if anamnez_life:
        for key, value in input_json.items():
            is_special = key in special_sections
            transformed = transform_node(key, value, is_special_section=is_special)
            if transformed:
                anamnez_life["successors"].append(transformed)

    return output


def main(input_json=None, filename=""):
    if not input_json:
        input_json = {
          "Сопутствующие и хронические заболевания": [
            {
              "Вирусные гепатиты": "отрицает",
              "ТВС": "отрицает",
              "Венерические заболевания": "отрицает"
            }
          ],
          "Перенесенные заболевания, травмы, операции": [
            {
              "Заболевания": {
                "Качественные значения": ["ЯБЖ", "ремиссия"]
              },
              "Травмы": {
                "Качественные значения": []
              },
              "операции": {
                "Качественные значения": []
              }
            }
          ],
          "Аллергологический анамнез": [
            {
              "Наличие аллергии": [
                {
                  "Качественные значения": ["аллергия отсутствует"]
                }
              ]
            }
          ],
          "Вредные привычки": [
            {
              "Курение": [
                {
                  "Присутствие": {
                    "Качественные значения": ["имеется"],
                    "Числовые значения": []
                  },
                  "Количество (штук в день)": {
                    "Качественные значения": [],
                    "Числовые значения": [1.0]
                  }
                }
              ]
            }
          ]
        }



    else:
        input_json = json.loads(input_json)

    output_json = transform_json(input_json, filename)

    # Для отладки
    # with open('output.json', 'w', encoding='utf-8') as f:
    #     json.dump(output_json, f, ensure_ascii=False, indent=2)
    #
    # print("Преобразование завершено. Результат сохранен в output.json")
    return output_json

if __name__ == "__main__":
    print(main())