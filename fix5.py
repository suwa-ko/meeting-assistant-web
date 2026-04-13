with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('+= \\<div', "+= '<div")
text = text.replace('\\ + modelTypeStr + \\</div>', "' + modelTypeStr + '</div>")
text = text.replace('</div>\\;', "</div>';")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
