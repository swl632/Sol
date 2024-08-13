import plugins
from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common import const
from common.log import logger
from config import conf
from plugins import *
from plugins.solitaire.activitydb import ActivityDB
import re

SEARCH_ALL_ACTIVITY = ["查询所有活动"]
SEARCH_ACTIVITY = ["查询", "查询活动"]
ADD_ACTIVITY = ["创建活动"]
DEL_ACTIVITY = ["删除活动"]
ADD_ACTIVITY_MEMBER = ["参加", "报名"]
HELP_ADD_ACTIVITY_MEMBER = ["代参加","代报名"]
DEL_ACTIVITY_BEMBER = ["退出", "取消"]
HELP_DEL_ACTIVITY_BEMBER = ["代退出", "代取消"]


@plugins.register(
    name="solitaire",
    desc="群内报名接龙",
    version="0.2.4",
    author="shiwanli",
    desire_priority=900,
)
class Solitaire(Plugin):
    def __init__(self):
        super().__init__()
        self.activity = ActivityDB()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context


    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return

        if e_context["context"].get("isgroup", False):
            nick_name = e_context["context"]["msg"].actual_user_nickname
        else:
            nick_name = e_context["context"]["msg"].from_user_nickname
        logger.debug(f"======================================================================={e_context["context"]}")
        logger.debug(f"======================================================================={e_context["context"]["msg"]}")
        content = e_context["context"].content.strip()
        logger.debug(f"[Solitaire] on_handle_context. content:{content}")
        content = content.split()
        reply_text = ""
        reply_flag = "handle"

        # 查询所有活动
        if content[0] in SEARCH_ALL_ACTIVITY:
            reply_text = self.query_all_activity()
        # 查询特定活动
        elif content[0] in SEARCH_ACTIVITY:
            reply_text = self.query_one_activity(content[1])

        # 创建活动
        elif content[0] in ADD_ACTIVITY:
            try:
                content.pop(0)
                pattern = "(.+?)：(.+)"
                activity_name = ""
                activity_describe = ""
                activity_number = 0
                for parameter in content:
                    matches = re.findall(pattern, parameter)
                    key = matches[0][0]
                    value = matches[0][1]

                    if key == "活动名称":
                        activity_name = value
                    elif key == "活动描述":
                        activity_describe = value
                    elif key == "活动人数":
                        activity_number = int(value)

                reply_text = self.create_activity(activity_name, activity_describe, activity_number)
                reply_text += self.query_all_activity()
            except Exception:
                reply_text = "创建活动失败"

        # 删除活动
        elif content[0] in DEL_ACTIVITY:
            reply_text = self.delete_activity(content[1])
            reply_text += self.query_all_activity()

        # 参加活动
        elif content[0] in ADD_ACTIVITY_MEMBER:
            reply_text = self.add_member(content[1], nick_name)
            reply_text += self.query_one_activity(content[1])
        # 代替报名活动
        elif content[0] in HELP_ADD_ACTIVITY_MEMBER:
            try:
                # 假设命令格式为 "代替 <代替人名> <活动名称>"
                if len(content) < 3:
                    reply_text = "命令格式错误，正确格式：代报名/代参加 <代替人名> <活动名称>"
                else:
                    # 获取代替人名和活动名称
                    replace_name = content[1]
                    activity_name = content[2]
                    # 构造新的nick_name
                    # 检查nick_name是否具有代替权限
                    if nick_name in ["石万里", "天天", "玟 爱米粒"]:
                        new_nick_name = f"{replace_name}"
                        # 使用新的nick_name进行报名
                        reply_text = self.add_member(activity_name, new_nick_name)
                        reply_text += self.query_one_activity(activity_name)
                    else:
                        # 如果没有代替权限，打印错误信息
                        print("没有替代权限")
                        reply_text = "没有替代权限"
            except Exception as e:
                reply_text = f"代替报名失败：{e}"
                logger.error(f"[Solitaire] ERROR: {e}")
        # 退出活动
        elif content[0] in HELP_DEL_ACTIVITY_BEMBER:
            # reply_text = self.delete_member(content[1], nick_name)
            # reply_text += self.query_one_activity(content[1])
            try:
                # 假设命令格式为 "代替 <代替人名> <活动名称>"
                if len(content) < 3:
                    reply_text = "命令格式错误，正确格式：代退出/代取消 <代替人名> <活动名称>"
                else:
                    # 获取代替人名和活动名称
                    replace_name = content[1]   #代替人名
                    activity_name = content[2]  #代替活动
                    # 构造新的nick_name
                    # 检查nick_name是否具有代替权限
                    if nick_name in ["石万里", "天天", "玟 爱米粒"]:
                        new_nick_name = f"{replace_name}"
                        # 使用新的nick_name进行取消报名
                        reply_text = self.delete_member(activity_name, new_nick_name)
                        reply_text += self.query_one_activity(activity_name)
                    else:
                        # 如果没有代替权限，打印错误信息
                        print("没有替代权限")
                        reply_text = "没有替代权限"
            except Exception as e:
                reply_text = f"代取消失败：{e}"
                logger.error(f"[Solitaire] ERROR: {e}")
                # 退出活动
        elif content[0] in DEL_ACTIVITY_BEMBER:
            reply_text = self.delete_member(content[1], nick_name)
            reply_text += self.query_one_activity(content[1])
        else:
            reply_flag = "pass"

        self.handel_reply(reply_text, reply_flag, e_context)

    def handel_reply(self, reply_text, reply_flag, e_context: EventContext):
        if reply_flag == "pass":
            e_context.action = EventAction.CONTINUE
        else:
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = reply_text
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

        
    def get_help_text(self, **kwargs):
        help_text = "群接龙\n"
        help_text += "[查询所有活动]：查询所有活动\n"
        help_text += "[查询单个活动]: 查询活动 <活动名称>\n"
        help_text += (
            "[创建单个活动]: 创建活动 活动名称：<活动名称> 活动描述：<活动描述> 活动人数：<活动人数>\n"
        )
        help_text += "[删除单个活动]：删除活动 <活动名称>\n"
        help_text += "[参加单个活动]：参加/报名 <活动名称>\n"
        help_text += "[代报名参加单个活动]：代参加/代报名 <代替人名> <活动名称>\n"
        help_text += "[退出单个活动]：退出/取消 <活动名称>\n"
        help_text += "[代退出单个活动]：代退出/代取消 <代替人名> <活动名称>\n"
        help_text += "==============================================================\n"
        return help_text

    # def get_help_text(self, **kwargs):
    #     help_text = "群接龙\n"
    #     help_text += "[查询所有活动]：查询所有活动\n"
    #     help_text += "[查询单个活动]: 查询活动 <活动名称>\n"
    #     help_text += (
    #         "[创建单个活动]: 创建活动 活动名称：<活动名称> 活动描述：<活动描述> 活动人数：<活动人数>\n"
    #     )
    #     help_text += "[删除单个活动]：删除活动 <活动名称>\n"
    #     help_text += "[参加单个活动]：参加/报名 <活动名称>\n"
    #     help_text += "[代报名参加单个活动]：代参加/代报名 <代替人名> <活动名称>\n"
    #     help_text += "[退出单个活动]：退出/取消 <活动名称>\n"
    #     help_text += "[代退出单个活动]：代退出/代取消 <代替人名> <活动名称>\n"
    #     help_text += "==============================================================\n"
    #     return help_text

    def query_all_activity(self):
        reply_text = "\n"
        result = self.activity.get_all_data()
        for activity in result:
            reply_text += "-------------\n"
            reply_text += f"活动名称: {activity['activity_name']}\n"
            reply_text += f"活动描述: {activity['describe']}\n"
            reply_text += "-------------\n"
        return reply_text

    def query_one_activity(self, activity_name):
        reply_text = "\n"
        try:
            activity = self.activity.query_activity(activity_name)[0]
            reply_text += f"活动名称: {activity['activity_name']}\n"
            reply_text += f"活动描述: {activity['describe']}\n"
            reply_text += f"活动人数: {activity['number']}\n"
            reply_text += f"活动人员: \n"
            for index, name in enumerate(activity["member"]):
                reply_text += f"{index+1}. {name}\n"
        except Exception as e:
            logger.error(f"[Solitaire] ERROR: {e}")

        return reply_text

    def create_activity(self, activity_name: str, activity_describe: str, activity_number: int):
        status = self.activity.add_activity(activity_name, activity_describe, activity_number)
        reply_text = "创建活动成功\n" if status else "创建活动失败\n"
        return reply_text

    def delete_activity(self, activity_name: str):
        status = self.activity.del_activity(activity_name)
        reply_text = "删除活动成功\n" if status else "删除活动失败\n"
        return reply_text

    def add_member(self, activity_name: str, nick_name: str):
        status = self.activity.add_member(activity_name, nick_name)
        reply_text = "报名活动成功\n" if status else "报名活动失败\n"
        return reply_text

    def delete_member(self, activity_name: str, nick_name: str):
        status = self.activity.del_member(activity_name, nick_name)
        reply_text = "退出活动成功\n" if status else "退出活动失败\n"
        return reply_text
