"""Functional tests use only isolated, explicitly synthetic projects."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('bootstrap',Path(__file__).with_name('bootstrap_project.py'))
build=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(build)
SKILL=Path(__file__).resolve().parents[1]

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='bootstrap-test-',dir=Path.cwd())
        self.root=Path(self.temp.name)/'project'
        self.manifest=json.loads((SKILL/'assets/manifest.example.json').read_text(encoding='utf-8'))
    def tearDown(self):self.temp.cleanup()
    def generated(self):
        build.apply(self.root,build.render(self.manifest))
        spec=importlib.util.spec_from_file_location('runtime',self.root/'scripts/projectctl.py')
        ctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(ctl)
        return ctl
    def command(self,name,*args,expected=0):
        result=subprocess.run([sys.executable,'-X','utf8',str(self.root/'scripts'/name),*args],cwd=self.root,capture_output=True)
        self.assertEqual(result.returncode,expected,result.stderr.decode('utf-8',errors='replace'))
        return json.loads(result.stdout.decode('utf-8'))
    def test_preview_has_no_filesystem_effect(self):
        files=build.render(self.manifest)
        self.assertEqual(build.preflight(self.root,files),[])
        self.assertFalse(self.root.exists())
    def test_collision_preserves_existing_project_and_writes_nothing(self):
        self.root.mkdir();(self.root/'AGENTS.md').write_text('Human-owned entry',encoding='utf-8')
        with self.assertRaises(ValueError):build.apply(self.root,build.render(self.manifest))
        self.assertEqual((self.root/'AGENTS.md').read_text(),'Human-owned entry')
        self.assertFalse((self.root/'spec.md').exists())
    def test_path_escape_in_outputs_and_artifact_policy_rejected(self):
        for path in ('../outside.txt','C:/outside.txt','/tmp/outside.txt','.git/config'):
            manifest=copy.deepcopy(self.manifest);manifest['work_orders'][0]['outputs']=[path]
            with self.assertRaises(ValueError):build.render(manifest)
        self.manifest['large_artifact_paths']=['../outside']
        with self.assertRaises(ValueError):build.render(self.manifest)
    def test_dependency_cycle_rejected(self):
        self.manifest['work_orders'][0]['depends_on']=['WO-01']
        with self.assertRaisesRegex(ValueError,'cycle'):build.render(self.manifest)
    def test_unknown_input_dependency_rejected(self):
        self.manifest['work_orders'][0]['required_inputs']=['nonexistent']
        with self.assertRaises(ValueError):build.render(self.manifest)
    def test_invented_confirmation_and_verified_commands_rejected(self):
        manifest=copy.deepcopy(self.manifest);manifest['decisions'][0]['source_quote']='A fabricated reply'
        with self.assertRaises(ValueError):build.render(manifest)
        self.manifest['work_orders'][0]['commands'][0]['status']='verified'
        with self.assertRaises(ValueError):build.render(self.manifest)
    def test_generated_framework_and_provenance_valid(self):
        ctl=self.generated();self.assertEqual(ctl.check(ctl.View(self.root))['status'],'PASS')
        self.assertLessEqual(len((self.root/'AGENTS.md').read_text(encoding='utf-8').splitlines()),90)
        self.assertFalse((self.root/'memory/approved/MEM-INITIAL-REQUEST.json').exists())
    def test_missing_input_blocks_first_work_order_without_false_success(self):
        self.manifest['work_orders'][0]['required_inputs']=['csv-source']
        self.generated();result=self.command('project_doctor.py',expected=2)
        self.assertEqual(result['prerequisites'],'BLOCKED')
        self.assertIn('not_tested',result['domain_execution'])
    def test_missing_tool_is_not_treated_as_environment_ready(self):
        self.manifest['tools']=[{'id':'tool-missing','kind':'executable','target':'nonexistent-bootstrap-fixture-tool-99391'}]
        self.manifest['work_orders'][0]['required_tools']=['tool-missing']
        self.generated();result=self.command('project_doctor.py',expected=2)
        self.assertIn('tool missing: tool-missing',result['blockers'])
    def test_real_runtime_route_and_cli_memory_lifecycle(self):
        self.generated();self.command('projectctl.py','check')
        doctor=self.command('project_doctor.py');self.assertEqual(doctor['prerequisites'],'PRESENT')
        result=subprocess.run([sys.executable,'-X','utf8',str(self.root/'scripts/projectctl.py'),'context','--work-order','WO-00'],cwd=self.root,capture_output=True,check=True)
        self.assertNotIn('## WO-01',result.stdout.decode('utf-8'))
        start=self.command('projectctl.py','task-start','--title','Fixture lifecycle','--session','SESSION-fixture','--actor','fixture-executor','--request-text','Synthetic fixture only')
        evidence=start['path']+'/request.md'
        self.command('projectctl.py','task-update','--task',start['task_id'],'--status','completed','--actor','fixture-executor','--summary','Fixture-only pass','--evidence',evidence)
        self.command('projectctl.py','propose','--task',start['task_id'],'--kind','local_experience','--claim','Fixture observation','--scope','fixture-only','--limitations','No real user project conclusion','--actor','fixture-executor','--evidence',evidence)
        self.assertEqual(self.command('projectctl.py','recall','--scope','fixture-only'),[])
        self.assertEqual(len(self.command('projectctl.py','recall','--scope','fixture-only','--include-candidates')),1)
    def test_research_software_and_general_have_project_specific_write_scopes(self):
        for domain,prefix in [('research','models/working/'),('software','src/'),('general','outputs/working/')]:
            manifest=copy.deepcopy(self.manifest);manifest['domain']=domain
            policy=json.loads(build.render(manifest)['configs/governance.policy.json'])
            self.assertIn(prefix,policy['executor_prefixes'])
            if domain!='research':self.assertNotIn('models/coupons/',policy['executor_prefixes'])
    def test_staged_policy_used_and_executor_cannot_promote_formal_files(self):
        ctl=self.generated()
        subprocess.run(['git','init',str(self.root)],capture_output=True,check=True)
        subprocess.run(['git','-C',str(self.root),'add','.'],capture_output=True,check=True)
        view=ctl.View(self.root,staged=True)
        ctl.guard_changes(view,[('A','AGENTS.md')],'steward')
        with self.assertRaises(ctl.PolicyError):ctl.guard_changes(view,[('A','AGENTS.md')],'executor')
        path=self.root/'configs/governance.policy.json';policy=json.loads(path.read_text(encoding='utf-8'));policy['executor_prefixes'].append('secret/')
        path.write_text(json.dumps(policy),encoding='utf-8')
        (self.root/'secret').mkdir();(self.root/'secret/item.txt').write_text('fixture',encoding='utf-8')
        subprocess.run(['git','-C',str(self.root),'add','secret/item.txt'],capture_output=True,check=True)
        with self.assertRaises(ctl.PolicyError):ctl.guard_changes(ctl.View(self.root,staged=True),[('A','secret/item.txt')],'executor')
    def test_source_tampering_and_reusing_approval_for_changed_bytes_rejected(self):
        ctl=self.generated();view=ctl.View(self.root)
        (self.root/'AGENTS.md').write_text('Changed beyond approved initial content',encoding='utf-8')
        with self.assertRaises(ctl.PolicyError):ctl.guard_changes(view,[('A','AGENTS.md')],'steward')
        (self.root/'records/requests/REQ-BOOTSTRAP.md').write_text('Different request',encoding='utf-8')
        with self.assertRaises(ctl.PolicyError):ctl.check(view)

    def test_moved_unicode_space_path_and_real_git_hook(self):
        self.generated()
        moved=self.root.parent/'portable 项目 with spaces';self.root.rename(moved);self.root=moved
        self.command('projectctl.py','check')
        self.assertEqual(self.command('project_doctor.py')['prerequisites'],'PRESENT')
        def git(*args,env=None):
            return subprocess.run(['git','-C',str(self.root),*args],capture_output=True,env=env)
        self.assertEqual(git('init').returncode,0)
        self.assertEqual(git('config','user.name','Synthetic fixture').returncode,0)
        self.assertEqual(git('config','user.email','fixture@local.invalid').returncode,0)
        configured=subprocess.run([sys.executable,str(self.root/'scripts/configure_project_git.py')],capture_output=True)
        self.assertEqual(configured.returncode,0,configured.stderr.decode('utf-8',errors='replace'))
        self.assertEqual(git('add','.').returncode,0)
        self.assertNotEqual(git('commit','-m','executor fixture should fail',env=dict(os.environ,PROJECT_ROLE='executor')).returncode,0)
        result=git('commit','-m','synthetic bootstrap only',env=dict(os.environ,PROJECT_ROLE='steward'))
        self.assertEqual(result.returncode,0,(result.stdout+result.stderr+git('status','--short').stdout).decode('utf-8',errors='replace'))

if __name__=='__main__':unittest.main(verbosity=2)
