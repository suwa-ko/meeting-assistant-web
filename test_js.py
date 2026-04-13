import re, json
with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

s = text.find('<script>') + 8
e = text.rfind('</script>')
js = text[s:e]

def is_matching(text):
    stack = []
    # simplify by skipping strings literals
    i = 0
    while i < len(text):
        c = text[i]
        if c in '\"\'':
            end_c = c
            i += 1
            while i < len(text):
                if text[i] == '\\\\': i += 2; continue
                if text[i] == end_c: break
                i+=1
        elif c in '{(': stack.append((c, i))
        elif c == '}':
            if not stack or stack[-1][0] != '{': print('Mismatch } at', i, text[max(0, i-50):i+50]); return False
            stack.pop()
        elif c == ')':
            if not stack or stack[-1][0] != '(': print('Mismatch ) at', i, text[max(0, i-50):i+50]); return False
            stack.pop()
        i += 1
    if stack:
        print('Unclosed:', stack[-1])
        return False
    return True

if is_matching(js): print('All good!')
