print("Opening Google and YouTube...")
browserOpen('https://www.google.com')
browserOpen('https://www.youtube.com')

print("Checking for errors in main.py...")
result = runCommand('python -m py_compile main.py')
if 'error' in result.lower():
    print("Errors found. Please fix them.")
else:
    print("No errors found. Project is ready!")