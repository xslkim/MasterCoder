"""
REQ-04: 对话消息管理器

实现对话消息的管理模块，维护当前会话的消息列表，支持添加不同角色的消息，
并在上下文超长时进行截断处理。
"""
from typing import List, Dict, Any, Optional


class MessageManager:
    """
    对话消息管理器
    
    维护一个有序消息列表，支持添加不同角色的消息，提供 token 估算和上下文截断功能。
    """
    
    def __init__(self):
        """初始化消息管理器"""
        self._messages: List[Dict[str, Any]] = []
    
    def add_message(
        self,
        role: str,
        content: Optional[str],
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None
    ) -> None:
        """
        追加一条消息到消息列表
        
        Args:
            role: 消息角色，取值为 "system" | "user" | "assistant" | "tool"
            content: 消息文本内容
            tool_calls: 可选，工具调用列表（仅 assistant 角色）
            tool_call_id: 可选，工具调用结果 ID（仅 tool 角色）
        """
        message: Dict[str, Any] = {"role": role}
        
        if content is not None:
            message["content"] = content
        
        if tool_calls is not None:
            message["tool_calls"] = tool_calls
        
        if tool_call_id is not None:
            message["tool_call_id"] = tool_call_id
        
        self._messages.append(message)
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """
        返回当前完整消息列表
        
        Returns:
            消息列表的副本
        """
        return self._messages.copy()
    
    def clear(self) -> None:
        """
        清空所有消息（保留 system 消息）
        
        仅保留 role 为 "system" 的消息
        """
        self._messages = [msg for msg in self._messages if msg["role"] == "system"]
    
    def get_token_estimate(self) -> int:
        """
        返回当前消息列表的估算 token 数
        
        Token 估算规则：以字符数 / 4 作为近似 token 数（简化实现）
        
        Returns:
            估算的 token 数量
        """
        total_chars = 0
        for message in self._messages:
            content = message.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
        
        return total_chars // 4
    
    def prepare_messages(self, max_context_tokens: int) -> Dict[str, Any]:
        """
        准备发送给 API 的消息列表，必要时进行截断
        
        检查总 token 估算值是否超过 max_context_tokens，若超出则从消息列表的第二条
        （跳过 index 0 的 system 消息）开始，逐条移除最早的消息，直到总量不超过限制。
        
        Args:
            max_context_tokens: 最大上下文 token 数
            
        Returns:
            包含以下字段的字典：
            - messages: 截断后的消息副本列表
            - truncated: 布尔值，表示是否发生了截断
        """
        # 创建消息列表的副本
        messages = self._messages.copy()
        
        # 如果没有消息或不需要截断，直接返回
        if not messages:
            return {"messages": [], "truncated": False}
        
        # 计算当前 token 估算
        def calculate_tokens(msgs: List[Dict[str, Any]]) -> int:
            total_chars = 0
            for msg in msgs:
                content = msg.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
            return total_chars // 4
        
        current_tokens = calculate_tokens(messages)
        
        # 如果不需要截断
        if current_tokens <= max_context_tokens:
            return {"messages": messages, "truncated": False}
        
        # 需要截断
        truncated_messages = messages.copy()
        
        # 从第二条消息开始移除（保留 index 0 的 system 消息）
        # 但是要小心：可能有多条 system 消息，或者第一条不是 system 消息
        # 策略：找到第一条非 system 消息的索引，然后逐个移除
        
        # 找到第一个非 system 消息的索引
        first_non_system_index = None
        for i, msg in enumerate(truncated_messages):
            if msg["role"] != "system":
                first_non_system_index = i
                break
        
        # 如果所有消息都是 system 消息，无法截断
        if first_non_system_index is None:
            return {"messages": truncated_messages, "truncated": False}
        
        # 从第一个非 system 消息开始，逐个移除，直到满足 token 限制
        while first_non_system_index < len(truncated_messages):
            current_tokens = calculate_tokens(truncated_messages)
            if current_tokens <= max_context_tokens:
                break
            
            # 移除第一个非 system 消息
            truncated_messages.pop(first_non_system_index)
        
        return {"messages": truncated_messages, "truncated": True}
