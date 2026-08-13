import zipfile
import os

def make_zip(output_path='submission.zip'):
    base = os.getcwd()
    include = ['src', 'README.md', 'requirements.txt', 'reports', 'tests']
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in include:
            if os.path.exists(name):
                if os.path.isfile(name):
                    z.write(name)
                else:
                    for root, dirs, files in os.walk(name):
                        for f in files:
                            full = os.path.join(root, f)
                            z.write(full, os.path.relpath(full, base))
    print('Created', output_path)

if __name__ == '__main__':
    make_zip()
