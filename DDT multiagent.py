import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# 页面配置
st.set_page_config(
    page_title="多智能体风控沙盘 - 采购三单匹配",
    page_icon="🛡️",
    layout="wide"
)

# 初始化session state
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "current_invoice" not in st.session_state:
    st.session_state.current_invoice = None
if "evidence_uploaded" not in st.session_state:
    st.session_state.evidence_uploaded = False
if "emergency_used_count" not in st.session_state:
    st.session_state.emergency_used_count = 0
if "emergency_pending_evidence" not in st.session_state:
    st.session_state.emergency_pending_evidence = []
if "feedback_history" not in st.session_state:
    st.session_state.feedback_history = []
if "rule_conflict_warning" not in st.session_state:
    st.session_state.rule_conflict_warning = None
if "adoption_rate" not in st.session_state:
    st.session_state.adoption_rate = 0.85
if "total_saved_hours" not in st.session_state:
    st.session_state.total_saved_hours = 42
if "current_tolerance" not in st.session_state:
    st.session_state.current_tolerance = 5.0

# 模拟ERP PO数据库
PO_DB = {
    "PO-123": {"amount": 10000.0, "quantity": 100, "supplier": "A公司", "type": "strategic"},
    "PO-456": {"amount": 20000.0, "quantity": 200, "supplier": "B公司", "type": "normal"},
    "PO-789": {"amount": 15000.0, "quantity": 150, "supplier": "C公司", "type": "high_risk"},
}

# 辅助函数：计算偏差
def calculate_deviation(inv_amount, po_amount):
    return (inv_amount - po_amount) / po_amount * 100 if po_amount != 0 else 0

# 数据质量守护：模拟缺失字段检测
def data_quality_guard(po_num, inv_amount, inv_qty):
    issues = []
    fill_values = {}
    if po_num not in PO_DB:
        return {"status": "fatal", "message": f"PO编号 {po_num} 不存在于ERP系统中", "issues": []}
    po_data = PO_DB[po_num]
    if inv_amount is None or inv_amount <= 0:
        issues.append("发票金额缺失")
        # 模拟填充（仅用于演示，不写回）
        avg_price = po_data["amount"] / po_data["quantity"]
        fill_values["inv_amount"] = avg_price * po_data["quantity"]
    if inv_qty is None or inv_qty <= 0:
        issues.append("发票数量缺失")
        fill_values["inv_qty"] = po_data["quantity"]
    if issues:
        # 计算置信度（模拟）
        confidence = 0.7 if len(issues) == 1 else 0.4
        return {
            "status": "incomplete",
            "issues": issues,
            "fill_values": fill_values,
            "confidence": confidence,
            "po_data": po_data
        }
    else:
        return {
            "status": "complete",
            "po_data": po_data,
            "inv_amount": inv_amount,
            "inv_qty": inv_qty
        }

# 风险研判（考虑数据质量标记）
def risk_assessment(po_data, inv_amount, inv_qty, tolerance, data_flag=None, is_strategic=False, has_evidence=False):
    po_amount = po_data["amount"]
    deviation = calculate_deviation(inv_amount, po_amount)
    abs_dev = abs(deviation)
    
    # 数据质量不完整时的特殊处理
    if data_flag and data_flag.get("status") == "incomplete":
        confidence = data_flag["confidence"]
        if confidence > 0.8:
            guidance = "数据基本完整，可先行放款，需事后补录"
            risk = "low"
            action = "可放款，生成补录任务"
        elif confidence > 0.5:
            guidance = "数据部分缺失，请人工核对后决定"
            risk = "pending"
            action = "等待人工决策"
        else:
            guidance = "关键数据缺失，请驳回至业务部门补充"
            risk = "reject"
            action = "驳回并推送工单"
        return {
            "risk": risk,
            "action": action,
            "guidance": guidance,
            "deviation": deviation,
            "need_manual": True
        }
    
    # 正常数据流程
    if has_evidence:
        risk = "low"
        action = "已降级放行（基于采购员举证）"
        guidance = "偏差已获合理解释，自动放行"
    elif is_strategic and abs_dev <= 10.0:
        risk = "medium"
        action = "发起复核工单（战略伙伴，暂不冻结）"
        guidance = "战略伙伴偏差在10%以内，建议人工复核"
    elif abs_dev <= tolerance:
        risk = "low"
        action = "自动放行，进入付款队列"
        guidance = f"偏差{deviation:.1f}%在阈值内"
    elif abs_dev <= 2 * tolerance:
        risk = "medium"
        action = "发起复核工单，通知采购/财务经理"
        guidance = f"偏差{deviation:.1f}%超出阈值，需复核"
    else:
        risk = "high"
        action = "冻结付款，紧急邮件通知三方"
        guidance = f"偏差{deviation:.1f}%严重超标，高风险"
    return {
        "risk": risk,
        "action": action,
        "guidance": guidance,
        "deviation": deviation,
        "need_manual": False
    }

# 反事实推演模拟（预先计算好的静态数据）
def get_insight_report():
    # 模拟离线推演结果
    return {
        "current": st.session_state.current_tolerance,
        "recommended": 6.5,
        "expected_benefit": {
            "reduced_false_positives": 9,
            "saved_hours": 1.5,
            "risk_increase": 0
        },
        "history_data_days": 30,
        "sample_size": 1230
    }

# 主界面
st.title("🛡️ 多智能体风控沙盘 - 采购三单匹配 (V2.2)")
st.caption("生产级演示 | 包含数据质量守护、三方协商、反事实推演、合规审批流、防滥用机制")

# 侧边栏：全局配置和紧急标记
with st.sidebar:
    st.header("⚙️ 沙盘控制")
    st.session_state.current_tolerance = st.slider(
        "当前金额容差阈值 (%)", 0.0, 20.0, st.session_state.current_tolerance, 0.5,
        help="当前生产环境使用的阈值"
    )
    urgent = st.checkbox("🚨 标记为紧急付款 (urgent_payment)", help="勾选后触发1h升级机制")
    supplier_type = st.selectbox("供应商类型", ["normal", "strategic", "high_risk"], format_func=lambda x: {"normal":"普通","strategic":"战略伙伴","high_risk":"高风险"}[x])
    
    st.markdown("---")
    st.metric("本月紧急放行已用次数", st.session_state.emergency_used_count, delta="限额3次" if st.session_state.emergency_used_count < 3 else "已达上限")
    st.metric("AI建议采纳率", f"{int(st.session_state.adoption_rate*100)}%")
    st.metric("累计节省工时", f"{st.session_state.total_saved_hours} 小时")

# 主区域：模拟ERP表单
st.header("📄 模拟ERP：创建采购发票")
with st.form("invoice_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        po_number = st.text_input("PO单号", value="PO-123")
        invoice_amount = st.number_input("发票金额 (元)", min_value=0.0, step=100.0, value=10800.0)
    with col2:
        invoice_qty = st.number_input("发票数量", min_value=0, step=1, value=100)
        # 模拟缺失字段测试选项
        missing_option = st.selectbox("模拟数据缺失", ["无", "金额缺失", "数量缺失", "PO不存在"])
    with col3:
        st.write("")
        st.write("")
        simulate_evidence = st.checkbox("模拟采购员已上传调价依据", help="勾选后代表AI协商成功")
    submitted = st.form_submit_button("提交发票，触发智能体")

# 处理提交
if submitted:
    # 根据缺失选项调整输入
    inv_amount = None if missing_option == "金额缺失" else invoice_amount
    inv_qty = None if missing_option == "数量缺失" else invoice_qty
    if missing_option == "PO不存在":
        po_number = "PO-INVALID"
    
    # 数据质量守护
    dq_result = data_quality_guard(po_number, inv_amount, inv_qty)
    
    if dq_result["status"] == "fatal":
        st.error(f"🚫 数据质量守护智能体: {dq_result['message']}")
        st.stop()
    
    # 展示数据质量结果
    if dq_result["status"] == "incomplete":
        st.warning("⚠️ 数据质量守护智能体检测到以下问题：")
        for issue in dq_result["issues"]:
            st.write(f"- {issue}")
        # 置信度二值化指引（不展示数字）
        conf = dq_result["confidence"]
        if conf > 0.8:
            guidance = "✅ 数据基本完整，可先行放款，需事后补录"
            st.info(guidance)
        elif conf > 0.5:
            guidance = "⚠️ 数据部分缺失，系统无法准确判断，请人工核对后决定"
            st.warning(guidance)
        else:
            guidance = "❌ 关键数据缺失，请驳回至业务部门补充完整后重新提交"
            st.error(guidance)
        # 使用填充值进行演示（仅展示，不落库）
        fill_vals = dq_result.get("fill_values", {})
        if fill_vals:
            st.caption(f"系统内部参考值：发票金额≈{fill_vals.get('inv_amount', 'N/A')}元 (仅用于推演，不修改ERP)")
        # 在这种情况下，强制人工决策，不自动执行
        st.session_state.current_invoice = {
            "dq_flag": True,
            "guidance": guidance,
            "po_data": dq_result["po_data"],
            "inv_amount": inv_amount,
            "inv_qty": inv_qty
        }
        st.session_state.submitted = True
    else:
        # 完整数据，继续三方协商
        po_data = dq_result["po_data"]
        inv_amount_val = dq_result["inv_amount"]
        inv_qty_val = dq_result["inv_qty"]
        deviation = calculate_deviation(inv_amount_val, po_data["amount"])
        
        st.subheader("🤖 多智能体协作日志")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("🕵️ 感知智能体：捕获发票")
            st.write(f"PO: {po_number}, 金额: {inv_amount_val}, 数量: {inv_qty_val}")
        with col2:
            st.info("📊 数据质量守护：完整")
            st.write("所有关键字段已就绪")
        with col3:
            st.info("⚖️ 研判智能体：计算偏差")
            st.write(f"金额偏差: {deviation:.1f}%")
        
        # 三方协商：偏差触发待举证任务
        if abs(deviation) > st.session_state.current_tolerance and not simulate_evidence:
            st.warning("🔔 偏差超出阈值，触发三方协商机制")
            st.write("系统已向采购员发起【待举证任务】：请在1个工作日内上传调价依据（截图/邮件/合同变更记录）")
            # 模拟紧急升级逻辑
            if urgent:
                st.error("🚨 紧急付款标记已激活！升级策略：")
                st.write("- 1小时内无响应 → 转派上级")
                st.write("- 2小时内无响应 → 转派总监强制放行")
                # 模拟一个倒计时（仅演示）
                st.warning("当前任务责任人：张三(采购员)，剩余响应时间 45分钟")
            else:
                st.info("常规任务，响应时限：1个工作日")
            # 模拟采购员上传证据（通过复选框模拟）
            if simulate_evidence:
                st.success("✅ 采购员已上传调价依据（模拟），系统将降级处理")
                has_evidence = True
            else:
                has_evidence = False
        else:
            has_evidence = simulate_evidence  # 如果偏差未超阈值，无需协商
        
        # 风险研判
        is_strategic = (supplier_type == "strategic")
        assessment = risk_assessment(
            po_data, inv_amount_val, inv_qty_val,
            st.session_state.current_tolerance,
            data_flag=None,
            is_strategic=is_strategic,
            has_evidence=has_evidence
        )
        
        st.subheader("📋 风险研判结果")
        if assessment["risk"] == "low":
            st.success(f"✅ 低风险 - {assessment['action']}")
        elif assessment["risk"] == "medium":
            st.warning(f"⚠️ 中风险 - {assessment['action']}")
        elif assessment["risk"] == "high":
            st.error(f"🔴 高风险 - {assessment['action']}")
        else:
            st.info(f"⏸️ {assessment['action']}")
        
        st.caption(assessment["guidance"])
        
        # 如果是紧急付款且高风险，展示强制放行选项
        if urgent and assessment["risk"] == "high" and st.session_state.emergency_used_count < 3:
            st.warning("🚨 紧急付款且高风险，是否启用强制放行（需双人确认）？")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ 强制放行 (双人确认)", key="force_release"):
                    st.session_state.emergency_used_count += 1
                    st.session_state.emergency_pending_evidence.append({
                        "po": po_number,
                        "amount": inv_amount_val,
                        "date": datetime.now(),
                        "requester": "模拟采购员"
                    })
                    st.success("强制放行已执行。系统已记录，请在7天内补传证据。")
                    st.info(f"本月剩余紧急放行次数: {3 - st.session_state.emergency_used_count}")
            with col_b:
                if st.button("❌ 维持冻结", key="keep_freeze"):
                    st.error("已冻结付款，等待进一步调查。")
        
        st.session_state.current_invoice = assessment
        st.session_state.submitted = True

# 反事实推演面板（始终显示）
st.header("📈 反事实推演沙盘 (动态合规沙盘)")
report = get_insight_report()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("当前阈值", f"{report['current']}%")
    st.metric("推荐阈值", f"{report['recommended']}%", delta=f"{report['recommended']-report['current']:.1f}%")
with col2:
    st.metric("预计每周减少误拦截", f"{report['expected_benefit']['reduced_false_positives']} 次")
    st.metric("节省人工工时", f"{report['expected_benefit']['saved_hours']} 小时/周")
with col3:
    st.metric("历史数据周期", f"{report['history_data_days']} 天")
    st.metric("样本量", f"{report['sample_size']} 笔")
st.caption("推演基于离线数仓T+1数据，反映过去30天已完结工单的统计特征。")

# 反馈按钮
col_fb1, col_fb2 = st.columns(2)
with col_fb1:
    if st.button("✅ 采纳并感谢", key="accept"):
        st.session_state.current_tolerance = report['recommended']
        st.session_state.adoption_rate = (st.session_state.adoption_rate * 9 + 1) / 10
        st.success(f"已采纳推荐阈值 {report['recommended']}%，当前阈值已更新。感谢您的反馈！")
        time.sleep(1)
        st.rerun()
with col_fb2:
    if st.button("❌ 不准，这次听我的", key="reject"):
        with st.form("feedback_form"):
            reason = st.selectbox("哪里不准？", ["阈值偏高", "阈值偏低", "场景不适用", "其他"])
            submitted_fb = st.form_submit_button("提交反馈")
            if submitted_fb:
                st.session_state.feedback_history.append({"reason": reason, "date": datetime.now()})
                st.session_state.adoption_rate = (st.session_state.adoption_rate * 9 + 0) / 10
                st.success("感谢反馈，AI将根据您的经验微调模型。")
                time.sleep(1)
                st.rerun()

st.markdown("---")
st.caption(f"上周推演建议采纳率 {int(st.session_state.adoption_rate*100)}%，累计节省工时 {st.session_state.total_saved_hours} 小时。您的反馈让AI持续进步。")

# 合规变更申请单示例（演示）
st.header("📋 合规参数变更工作流")
if st.button("生成变更申请单 (基于当前推荐阈值)", key="gen_approval"):
    # 损益换算标题
    title = f"【风控参数变更】申请将金额容差从{report['current']}%调整为{report['recommended']}%，预计每周减少{report['expected_benefit']['reduced_false_positives']}次无效拦截（节省{report['expected_benefit']['saved_hours']}小时），过去30天推演无新增风险漏过"
    st.success(f"✅ 已生成OA审批单：\n\n{title}\n\n审批流：业务主管 → 财务总监 → (变更>2%)内控 → IT执行")
    st.info("审批通过后系统将自动调用ERP接口修改参数，审计日志已记录。")

# 规则冲突检测演示
st.header("⚙️ 规则冲突检测 (零代码安全版)")
with st.expander("尝试添加一条可能冲突的规则"):
    new_rule = st.text_input("新规则描述", "战略供应商_金额容差_15%")
    if st.button("保存规则", key="save_rule"):
        # L1静态检测模拟
        if "战略" in new_rule and "15%" in new_rule:
            st.error("🚫 L1静态检测发现冲突：已有规则 '战略伙伴允许10%偏差'，同一字段不允许更高容差。请调整优先级或合并规则。")
        else:
            st.success("规则保存成功。L2动态检测将在后台运行，如有冲突将企微告警。")
            # 模拟异步告警
            st.info("后台检测中... (模拟异步，不阻塞)")
            time.sleep(1)
            st.warning("⚠️ 后台检测提示：新规则与'高风险地区_0%容差'存在交集冲突，建议复核。")

# 紧急放行事后催办演示
st.header("⏰ 紧急放行闭环监控")
if st.session_state.emergency_pending_evidence:
    st.write("以下紧急放行尚未补传证据：")
    for item in st.session_state.emergency_pending_evidence:
        days_passed = (datetime.now() - item["date"]).days
        st.write(f"- PO: {item['po']}, 金额: {item['amount']}, 已过 {days_passed} 天")
        if days_passed >= 7:
            st.error("⚠️ 超过7天未补证，该采购员紧急权限已降级为‘需总监审批’")
    if st.button("模拟补传证据", key="补传"):
        st.session_state.emergency_pending_evidence = []
        st.success("证据已补传，紧急权限恢复正常。")
else:
    st.info("暂无待补证记录")

# 底部说明
st.markdown("---")
st.caption("V2.2 生产级演示 | 包含数据质量二值化指引、紧急放行防滥用、反馈闭环、合规审批标题 | 所有操作均不修改真实ERP数据")
