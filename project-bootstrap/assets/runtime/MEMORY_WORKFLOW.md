# 任务和经验

在项目根目录，用实际可用Python运行以下命令。完整参数见scripts/projectctl.py --help。

```text
python -X utf8 scripts/projectctl.py status
python -X utf8 scripts/projectctl.py context --work-order WO-00
python -X utf8 scripts/projectctl.py recall --scope project
```

task-start保存真实请求、会话标签、执行者和输入哈希；它不授予新的授权。

```text
python -X utf8 scripts/projectctl.py task-start --title "本次任务" --session SESSION-local --actor executor --request-text "真实用户请求"
```

复制返回TASK-id后替换以下示例ID。先写本任务报告，task-update追加状态/结果与证据，不覆盖以前事件。每人/AI独立任务目录。

```text
python -X utf8 scripts/projectctl.py task-update --task TASK-id --status completed --actor executor --summary "完成、缺项和验证范围" --evidence work/tasks/TASK-id/report.md
python -X utf8 scripts/projectctl.py propose --task TASK-id --kind local_experience --scope "project:适用条件" --claim "有证据的经验" --limitations "未验证范围/反例" --actor executor --evidence work/tasks/TASK-id/report.md
```

候选始终proposed；没有新经验就不生成。recall默认只检索正式摘要，审查候选时显式加--include-candidates并打开选中来源。大型数据引用哈希清单与报告，不能只写“实验成功”。

steward审查候选后用plan-promotion生成精确预览。重大规则/方法经真实用户确认后，records/requests保留原句，records/approvals按schemas/approval.schema.json绑定候选和目标内容。记录者必须保留来源上下文并说明为何加入长期层，不能自造用户批准。

```text
python -X utf8 scripts/projectctl.py plan-promotion --candidate MEM-id --approval-id APP-id
python -X utf8 scripts/projectctl.py promote --candidate MEM-id --approval APP-id --role steward
python -X utf8 scripts/projectctl.py check
```

proposed不能因被AI重复引用就晋升。修订用新记录和supersedes；正式后继经确认后才替代默认检索。批准继续验证的推断仍是hypothesis。

执行者只暂存自己的允许文件，先运行guard --staged --role executor。维护者在真实授权范围下可用PROJECT_ROLE=steward提交，受保护修改仍需精确来源批准。换主机后启用本仓库hook，核实工具和输入；角色变量不是身份认证。
