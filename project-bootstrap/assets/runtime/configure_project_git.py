"""Enable the local project's hook after cloning or initialization."""
import argparse
from pathlib import Path
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();root=args.root.resolve()
    if not (root/'.git').exists() or not (root/'.githooks/pre-commit').is_file():
        parser.error('A project Git repository and its framework hook must exist.')
    subprocess.run(['git','-C',str(root),'config','--local','core.hooksPath','.githooks'],check=True)
    subprocess.run(['git','-C',str(root),'config','--local','project.python',str(Path(sys.executable).resolve()).replace('\\','/')],check=True)
    print('Local hook enabled; default role executor. This is a workflow guard, not identity authentication.')
if __name__=='__main__':main()
