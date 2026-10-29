"""Read-only prerequisite inventory; does not execute arbitrary project commands."""
import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def inspect_tool(tool):
    kind=tool['kind'];target=tool['target'];found=False;version=None
    if kind=='python_module':
        try:found=importlib.util.find_spec(target) is not None
        except (ImportError,ModuleNotFoundError,ValueError):found=False
        try:version=importlib.metadata.version(tool.get('distribution',target))
        except importlib.metadata.PackageNotFoundError:pass
        location=target
    else:
        path=Path(target);path=path if path.is_absolute() else ROOT/path
        location=shutil.which(target) if kind=='executable' else None
        location=location or (str(path) if path.is_file() else None);found=bool(location)
    return {'id':tool['id'],'kind':kind,'found':found,'location':location,'version_metadata':version,'execution_status':'not_tested'}
def diagnose(work_order=None):
    spec=importlib.util.spec_from_file_location('projectctl',ROOT/'scripts/projectctl.py')
    ctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(ctl)
    framework=ctl.check(ctl.View(ROOT));project=load('configs/project.json')
    environment=load('configs/environment.json')
    overlay=ROOT/'configs/environment.local.json'
    if overlay.is_file():
        local=json.loads(overlay.read_text(encoding='utf-8-sig'))
        overrides={x['id']:x for x in local.get('tools',[])}
        environment['tools']=[dict(x,**overrides.get(x['id'],{})) for x in environment['tools']]
    tools={x['id']:inspect_tool(x) for x in environment['tools']}
    wo=next((x for x in project['work_orders'] if x['id']==work_order),None) if work_order else project['work_orders'][0]
    if wo is None:raise ValueError('Unknown work order')
    blocked=[];inputs=[]
    for source in project['inputs']:
        if source['id'] not in wo['required_inputs']:continue
        file=Path(source['path']);file=file if file.is_absolute() else ROOT/file
        exists=file.exists()
        item={'id':source['id'],'exists':exists,'declared_status':source['status']}
        if source.get('sha256') and file.is_file():
            import hashlib
            item['hash_matches']=hashlib.sha256(file.read_bytes()).hexdigest()==source['sha256']
            if not item['hash_matches']:blocked.append('input hash mismatch: '+source['id'])
        inputs.append(item)
        if not exists:blocked.append('input missing: '+source['id'])
    for tool in wo['required_tools']:
        if not tools[tool]['found']:blocked.append('tool missing: '+tool)
    for dependency in wo['depends_on']:blocked.append('predecessor acceptance must be reviewed: '+dependency)
    for question in project.get('open_questions',[]):
        if wo['id'] in question['blocks_work_orders']:blocked.append(question['question'])
    return {'framework':framework,'python':{'executable':sys.executable,'version':platform.python_version()},'host':platform.platform(),'work_order':wo['id'],'tools':list(tools.values()),'inputs':inputs,'prerequisites':'BLOCKED' if blocked else 'PRESENT','blockers':blocked,'domain_execution':'not_tested; retain an actual work-order smoke/acceptance report','readiness':'framework_initialized' if blocked else 'prerequisites_present_pending_task_smoke'}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-order');parser.add_argument('--output')
    args=parser.parse_args();result=diagnose(args.work_order)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        destination=(ROOT/args.output).resolve()
        if not destination.is_relative_to(ROOT) or not destination.relative_to(ROOT).as_posix().startswith(('reports/','work/')) or destination.suffix!='.json':
            parser.error('Output must be a project-relative JSON under reports/ or work/.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('x',encoding='utf-8',newline='\n') as file:file.write(text)
    print(text);return 2 if result['blockers'] else 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError) as error:
        print('DOCTOR FAILED: '+str(error),file=sys.stderr);raise SystemExit(2)
