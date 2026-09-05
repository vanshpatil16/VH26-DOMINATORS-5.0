"""Find the unclosed triple-quote in analyzer.py."""
lines = open('codegate/analyzer.py', 'r', encoding='utf-8').readlines()
in_docstring = False
start_line = 0
for i, line in enumerate(lines):
    n = line.count('"""')
    for _ in range(n):
        if in_docstring:
            in_docstring = False
            print(f"  CLOSE  at line {i+1}: {line.rstrip()[:80]}")
        else:
            in_docstring = True
            start_line = i + 1
            print(f"  OPEN   at line {i+1}: {line.rstrip()[:80]}")

if in_docstring:
    print(f"\n==> UNCLOSED docstring that opened at line {start_line}")
else:
    print("\nAll triple-quotes are balanced (hmm, the issue might be a triple-single-quote or something else)")
