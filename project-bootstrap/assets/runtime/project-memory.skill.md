---
name: project-memory
description: 在当前项目登记任务、保存有来源的经验候选、按范围读取正式记忆并凭真实具体批准晋升；用于任务收尾、经验复用和记忆纠错。
---

# 项目记忆

从[索引](../../context/INDEX.md)选择上下文，权限见[治理](../../context/GOVERNANCE.md)，命令见[记忆流程](../../context/MEMORY_WORKFLOW.md)。

task-start保存真实请求与来源会话，task-update追加局部事件/证据；propose仅产生带kind、scope、limitations和证据哈希的候选。没有可重用新经验就不写。recall默认正式摘要，候选审查显式include-candidates。

维护者审查具体范围/反例，plan-promotion生成预览，重大方法/规则得到真实用户明确批准后再promote。批准绑定源原句、候选版本及目标内容；executor不能晋升。修订追加supersedes，保留原始依据。普通局部更新无需重复审批。

Git/role是流程护栏，不能认证人类或隔离共享账号。当前用户指令优先于历史；不把假设、软件通过或他人摘要提升成来源事实。
