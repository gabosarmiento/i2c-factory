def process(data):
    result = []
    for item in data:
        if item.get('value'):
            result.append(item['value'] * 2)
        else:
            result.append(None)
    return result
