import assert from 'node:assert/strict';
import {spawn, execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync,mkdtempSync,existsSync,chmodSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
const source=readFileSync(process.argv[2],'utf8');
const defs=source.slice(source.indexOf('function runGitCommand'),source.indexOf('class GitWorkflowMCPServer'));
let failures=0;
for (const kind of ['fsmonitor','fsmonitor-long','external','external-staged','textconv','textconv-staged','write-hook']) {
 const root=mkdtempSync(path.join(tmpdir(),'git-readonly-'));
 const env={PATH:process.env.PATH,HOME:root,GIT_CONFIG_NOSYSTEM:'1'};
 const git=(...args)=>execFileSync('git',args,{cwd:root,env,stdio:'pipe'});
 git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
 writeFileSync(path.join(root,'file.txt'),'before\n');git('add','.');git('commit','-qm','baseline');
 const marker=path.join(root,'marker');
 const helper=path.join(root,'helper.sh');
 writeFileSync(helper,'#!/bin/sh\nprintf fixture > "'+marker+'"\n');chmodSync(helper,0o755);
 writeFileSync(path.join(root,'file.txt'),'after\n');
 if(kind.endsWith('-staged'))git('add','file.txt');
 if(kind.startsWith('fsmonitor'))git('config','core.fsmonitor',helper);
 if(kind.startsWith('external'))git('config','diff.external',helper);
 if(kind.startsWith('textconv')){git('config','diff.fixture.textconv',helper);writeFileSync(path.join(root,'.gitattributes'),'*.txt diff=fixture\n');}
 if(kind==='write-hook'){const hook=path.join(root,'.git/hooks/pre-commit');writeFileSync(hook,readFileSync(helper));chmodSync(hook,0o755);}
 const context=vm.createContext({spawn,path,process:{env},WORKSPACE_ROOT:root});
 vm.runInContext(defs,context);
 try {
  const result=await vm.runInContext(kind.startsWith('fsmonitor')?'gitStatus({porcelain:'+(!kind.endsWith('-long'))+'})':kind==='write-hook'?'gitCommit({message:"fixture",allowEmpty:true})':'gitDiff({staged:'+kind.endsWith('-staged')+',pathspec:"file.txt"})',context);
  if(kind==='write-hook')assert.ok(existsSync(marker),'explicit commit hook behavior preserved');
  else {assert.ok(!existsSync(marker),kind+' must not execute repository helper');if(!kind.startsWith('fsmonitor'))assert.ok(result.stdout.includes('+after'),'ordinary diff preserved');}
  console.log('PASS '+kind);
 } catch(error){failures++;console.log('FAIL '+kind+': '+error.message);}
}
process.exitCode=failures?1:0;
