# 第 5 步知识检索评测报告

## 汇总结果

- 应该找到资料的问题：16 条
- 第一条结果来源正确：16 条，命中率 100.0%
- 前三条包含正确来源：16 条，命中率 100.0%
- 知识库外问题：4 条
- 正确拒绝知识库外问题：4 条，拒绝率 100.0%
- 当前相关度阈值：0.200
- 知识内问题最低相关度：0.297
- 知识外问题最高相关度：0.167

## 逐题结果

| 问题 | 预期 | 实际第一来源 | 最高相关度 | 结果 |
|---|---|---|---:|---|
| 新员工入职后多久能拿到账号 | account_policy.md | account_policy.md | 0.453 | 通过 |
| 账号连续验证失败会锁多久 | account_policy.md | account_policy.md | 0.365 | 通过 |
| 员工调岗以后权限怎么处理 | account_policy.md | account_policy.md | 0.388 | 通过 |
| 离职账号中的数据会保留多长时间 | account_policy.md | account_policy.md | 0.443 | 通过 |
| 一线城市出差住宿每晚最多多少钱 | reimbursement_policy.md | reimbursement_policy.md | 0.443 | 通过 |
| 报销发票丢失以后怎么办 | reimbursement_policy.md | reimbursement_policy.md | 0.374 | 通过 |
| 费用发生后多少天内要提交报销 | reimbursement_policy.md | reimbursement_policy.md | 0.344 | 通过 |
| 客户招待费用需要谁批准 | reimbursement_policy.md | reimbursement_policy.md | 0.438 | 通过 |
| 付款成功但订单仍未支付应该怎么办 | payment_guide.md | payment_guide.md | 0.537 | 通过 |
| 一个订单重复扣款如何退款 | payment_guide.md | payment_guide.md | 0.574 | 通过 |
| 银行卡退款一般多久可以到账 | payment_guide.md | payment_guide.md | 0.366 | 通过 |
| 电子发票什么时候可以申请 | payment_guide.md | payment_guide.md | 0.566 | 通过 |
| 提交系统故障需要提供哪些资料 | technical_guide.md | technical_guide.md | 0.297 | 通过 |
| 核心服务完全不可用属于什么等级 | technical_guide.md | technical_guide.md | 0.336 | 通过 |
| 上传文件大小有什么限制 | technical_guide.md | technical_guide.md | 0.513 | 通过 |
| 系统每周什么时候进行维护 | technical_guide.md | technical_guide.md | 0.465 | 通过 |
| 公司食堂今天中午吃什么 | 应拒绝 | 已拒绝 | 0.057 | 通过 |
| 办公楼停车位如何申请 | 应拒绝 | 已拒绝 | 0.108 | 通过 |
| 员工生日会安排在几月 | 应拒绝 | 已拒绝 | 0.167 | 通过 |
| 公司是否允许在办公室养宠物 | 应拒绝 | 已拒绝 | 0.075 | 通过 |

## 说明

当前评测集规模较小，主要用于防止代码修改破坏已有检索效果。真实上线前应使用业务人员编写的更多问题，并把问题按主题、难度和表达方式分类评测。

当前阈值根据小型开发问题集调整，因此这个结果不能视为完全独立的最终测试。后续需要另建没有参与阈值选择的问题集进行验证。
