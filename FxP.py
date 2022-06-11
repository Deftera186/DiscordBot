import hashlib
import re
import socketio
import asyncio
import aiohttp
from typing import List, Dict, Optional, Union
import json
import logging
import base64
from xml.etree import ElementTree

logging.getLogger('asyncio').setLevel(logging.CRITICAL)

class obj:
    ''' class that will be used for most events to allow attribute access '''
    def __init__(self, **entries):
        ''' The struct method ''' 
        self.__dict__.update(entries)

class Thread(obj):
    ''' class for thread object '''
    def __init__(self, forum_id: str, **entries):
        super().__init__(**entries)
        self.forum_id = forum_id
    
    async def html(self) -> str:
        ''' Returns the html of the first post in the thread '''
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.fxp.co.il/showthread.php", params={'t':self.id}) as resp:
                return re.search(r"<blockquote class=\"postcontent restore\" itemprop=\"articleBody\">(.*?)</blockquote>", await resp.text(), re.DOTALL).group(1)
            
    async def content(self) -> str:
        ''' Returns the first post in a particular thread as vBulletin code (with <br> so it will be ready to send)'''
        return (await vBulletin.editor_switch(await self.html(), parsetype=self.forum_id)).replace("\n", "<br>")
        
class WrongCredentials(Exception):
    """Exception raised for errors in username or password"""

    def __init__(self, username, password):
        super().__init__(
            f"username {username} or password {password} is incorrect")


class ConnectionFailed(Exception):
    """Exception may raised when connection to a forum or thread failed"""

    def __init__(self):
        super().__init__("Connection failed, maybe something is wrong with your account or the id is invalid.")


class RateLimit(Exception):
    '''Exception raised when ratelimited by server'''

    def __init__(self):
        super().__init__("Rate Limit")


class FxP:
    #### static variables ####
    THREAD = "THREAD"
    FORUM = "FORUM"

    def __init__(self, username: str, password: str) -> None:
        ''' The struct method ''' 
        self.username = username
        self.password = password
        self.securitytoken = 'guest'
        self.wrappers = list()

    async def _login(self) -> bool:
        ''' A function that is used to connect and obtain essential data so that everything works properly.
        called as part of FxP.run(), but can be used if you do not want to use events.
        note this function will raise WrongCredentials exception when login was failed.
        '''
        self.session = aiohttp.ClientSession()
        _pass = hashlib.md5(self.password.encode()).hexdigest()
        resp = await self.session.post('https://www.fxp.co.il/login.php', params={
            'web_fast_fxp': 1
        }, data={
            'vb_login_username': self.username,
            'securitytoken': self.securitytoken,
            'do': 'login',
            'cookieuser': 1,
            'vb_login_md5password': _pass,
        })
        if "ניסית להתחבר במספר הפעמים המרבי!" in await resp.text():
            raise RateLimit()
        try:
            fxp_source = await (await self.session.get("https://www.fxp.co.il/")).text()
            if "Rate Limit" in fxp_source:
                raise RateLimit()
            self.send = re.search(
                r"\{\"userid[^']+",
                fxp_source).group()
            self.securitytoken = re.search(
                r"\d\w+\-\w*", fxp_source).group()
            self.user_id = resp.cookies.get("bb_userid").value
            self._forum = self._thread = -1
        except AttributeError:
            raise WrongCredentials(self.username, self.password)
        return True

    def run(self) -> None:
        '''Doing some necessary things for everything to work properly:
        1) Logs in to the user and saves the session
        2) Connects to the main page WebSocket
        3) execute all the decorated functions
        '''
        async def _run() -> None:
            await self._login()
            #### connecting to the socket ####
            self.sio = socketio.AsyncClient()
            @self.sio.on('connect')
            async def connect():
                await self.sio.send(self.send)
            await self.sio.connect('https://socket5.fxp.co.il')
            for wrapper in self.wrappers:
                await wrapper
            await self.sio.wait()
        asyncio.run(_run())

    async def _connect(self, _id: str, t_f: str) -> bool:
        '''Note that this is a private function and should not be used in your projects
        method for switching forum or thread.
        t_f can be either SELF.THREAD or SELF.FORUM
        returns True if connected.
        returns False if failed.
        '''
        if t_f == self.FORUM:
            if _id == self._forum:
                return True
            try:
                self._forum = _id
                self.send = re.search(
                    r"\{\"userid[^']+",
                    await (await self.session.get("https://www.fxp.co.il/forumdisplay.php?f=" + str(self._forum))).text()).group()
                await self.sio.send(self.send)
            except BaseException:
                return False
            return True
        elif t_f == self.THREAD:
            if _id == self._thread:
                return True
            try:
                self._thread = _id
                self.send = re.search(
                    r"\{\"userid[^']+",
                    await (await self.session.get("https://www.fxp.co.il/showthread.php?t=" + str(self._thread))).text()).group()
                await self.sio.send(self.send)
            except Exception as e:
                return False
            return True
        else:
            return False

    async def close(self):
        ''' You should call this command at the end of the program if you do not intend to use the bot 24/7 '''
        await self.session.close()
    
    async def update_profile_pic(self, filepath: str) -> bool:
        ''' Updates your profile picture

        Parameters:
        filepath(str): Full / partial path to the image file
        '''
        base = f'data:image/jpeg;base64,' + base64.b64encode(open(filepath, "rb").read()).decode()
        async with self.session.post("https://profile.fcdn.co.il/imageprofile", data={
            'b': '1',
            'base': base,
            'uid': self.user_id}) as resp:
            profile_url = json.loads(await resp.text())['image_link']
            async with self.session.post("https://www.fxp.co.il/private_chat.php", data={
                'do': 'update_profile_pic',
                'profile_url': profile_url,
                'user_id': self.user_id,
                'securitytoken': self.securitytoken}) as response:
                    if await response.text() == 'ok':
                        return True
        return False
                                    
    async def add_like(self, postid: str) -> None:
        '''Adds a like to a post

        Parameters:
        postid (str): The id of the comment you want to like'''
        await self.session.post("https://www.fxp.co.il/ajax.php", data={
            'do': 'add_like',
            'postid': postid,
            'securitytoken': self.securitytoken
        }, headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36"})

    async def follow_user(self, userid: str) -> dict:
        '''Follows a user

        Parameters:
        userid(str): The id of the user you want to follow'''
        resp = await self.session.post("https://www.fxp.co.il/ajax.php", data={
            'do': 'followuser',
            'userid': userid,
            # Uses a token of a verified device, should appear in the
            # following.php.
            'playerid': "7a0167b6-4915-4ed6-87bb-093f11b12c1d",
            'securitytoken': self.securitytoken})
        return json.loads(await resp.text())

    async def post_thread(self, f: str, subject: str, message: str, prefixid: Optional[str] = '1', signature: Optional[bool] = True) -> Union[str, bool]:
        '''Creates a new thread

        Parameters:
        f (str): The id of the forum
        subject (str): Thread Title
        message (str): thread content
        prefixid (str): The id of the prefix you want to add, the default is without prefix.
        signature (bool): Show signature in thread?

        Returns:
        (str): If the thread posting was successful, the id of the thread will be returned
        (bool): If the therad opening fails, False will be returned
        '''
        resp = await self.session.post("https://www.fxp.co.il/newthread.php", params={
            'do': 'postthread',
            'f': f}, data={
                'prefixid': prefixid,
                'subject': subject,
                'message_backup': message,
                'message': message,
                'wysiwyg': 1,
                'securitytoken': self.securitytoken,
                'f': f,
                'do': 'postthread',
                'loggedinuser': self.user_id,
                'signature': int(signature),
                'parseurl': '1'})
        try:
            return resp.url.query['t']
        except KeyError:
            return False

    async def post_reply(self, t: str, message: str, signature: Optional[bool] = True) -> None:
        '''Post a comment in a thread

        Parameters:
        t (str): The id of the thread where you want to post a comment
        message (str): the message content
        signature (bool) [Optional]: Show user signature in post?'''
        await self.session.post("https://www.fxp.co.il/newreply.php", params={
            'do': 'postreply',
            't': t}, data={
                'securitytoken': self.securitytoken,
                'ajax': '1',
                'message_backup': message,
                'message': message,
                'wysiwyg': 1,
                'signature': int(signature),
                'fromquickreply': 1,
                'do': 'postreply',
                't': t,
                'specifiedpost': 0,
                'parseurl': 1,
                'loggedinuser': self.user_id
        }
        )

    async def post_poll(self, t: str, question: str, options: list) -> None:
        ''' Creating a poll in your thread

        Parameters:
        t(str): the thread id
        question(str): the poll question
        options(list): list of the options
        '''
        data = {
            'question': question,
            'polloptions': len(options),
            'parseurl': '1',
            'securitytoken': self.securitytoken,
            't': t,
            'do': 'postpoll'}
        for i, option in enumerate(options, 1):
            data[f"options[{i}]"] = option
        await self.session.post("https://www.fxp.co.il/poll.php", params={
            'do': 'postpoll',
            't': t}, data=data)

    async def poll_vote(self, pollid: str, optionnumber: Union[str, int]) -> None:
        ''' Vote in a poll.

        Parameters:
        pollid(str): the pollid
        optionnumber(int, str): Which option do you want to vote for? Note that the first option is 1 and not 0.
        '''
        await self.session.post("https://www.fxp.co.il/poll.php", params={
            'do' : 'pollvote',
            'pollid': pollid}, data={
                'optionnumber': optionnumber,
                'securitytoken': self.securitytoken,
                'do': 'pollvote',
                'pollid': pollid})
            
    async def insert_pm(self, recipients: Union[str, list], title: str, message: str, savecopy: Optional[bool] = True) -> str:
        ''' Creates new chat

        Parameters:
        recipients (str, list): Can be a string or a list of strings of the usernames of the person you want the message to be sent to
        title (str): The title of the chat
        message (str): the message
        savecopy (bool) [Optional]: should the message appear in chat.php?

        Returns:
        (str): the id of the last chat that was created'''
        recipients = ";".join(recipients) if isinstance(
            recipients, list) else recipients
        async with self.session.post("https://www.fxp.co.il/private.php", params={
            'do': 'insertpm'}, data={
                'recipients': recipients,
                'title': title,
                'message_backup': message,
                'message': message,
                'wysiwyg': 1,
                'securitytoken': self.securitytoken,
                'do': 'insertpm',
                'savecopy': int(savecopy),
                'signature': 1,
                'parseurl': 1}) as resp:
            return re.search(r"pmid=(\d+)", await resp.text()).group(1)

    async def send_pm(self, message: str, pmid: str, recipients: str, savecopy: Optional[bool] = True) -> Union[dict, bool]:
        '''Sends a private message to an existing chat

        Parameters:
        message (str): The message you want to send
        pmid (str): the id of the chat you want to send a message to
        recipients (str): Username of the other party in chat
        savecopy (bool) [Optional]: should the message appear in chat.php?

        Returns:
        (dict):
            message (str): The message you sent
            pmid (str): The id of the chat to which you sent the message to
            date (str): The date the message was sent
            time (str): The time in the date the message was sent
            parentpmid (str, NoneType): Probably None, can contain the pmid in some cases
            pmid_read (str): The id of the message you sent
            pmtextid (str): data-text-id HTML Attribute value

        (bool) if the message fails, False will be returned'''
        async with self.session.post("https://www.fxp.co.il/private_chat.php", data={
            'message': message,
            'fromquickreply': '1',
            'securitytoken': self.securitytoken,
            'do': 'insertpm',
            'pmid': pmid,
            'loggedinuser': self.user_id,
            'parseurl': '1',
            'signature': '1',
            'title': 'תגובה להודעה:',
            'forward': '0',
            'savecopy': int(savecopy),
            'fastchatpm': '1',
            'wysiwyg': '1',
            'recipients': recipients
        }) as resp:
            try:
                r_value = json.loads(await resp.text())
            except BaseException:
                r_value = False
            return r_value

    def on_new_thread(self, forum_id: str):
        ''' An event that will activate the decorated function as soon as
        there is a new thread in the specified forum.

        Separates from everything else because it returns a Thread object.
        Parameters:
        forum_id(str): Which forum to listen to?
        '''
        def decorator(func):
            async def wrapper(*args, **kwargs):
                if await self._connect(forum_id, self.FORUM):
                    @self.sio.on("newtread")
                    async def call(data):
                        await func(Thread(forum_id, **data))
                else:
                    raise ConnectionFailed()
            self.wrappers.append(wrapper())
            return wrapper
        return decorator
    
    @staticmethod
    async def add_member(username: str, password: str, email: str) -> Union[str, bool]:
        ''' Adding a member based on paramaters, returns the userid of the member that was created or False if creation was failed'''
        password_md5 = hashlib.md5(password.encode()).hexdigest()
        async with aiohttp.ClientSession() as session:
            async with session.post("https://www.fxp.co.il/register.php?do=addmember", data={'username': username, 'email': email, 'agree': 1, 'securitytoken': 'guest', 'do': 'addmember', 'password_md5': password_md5, 'passwordconfirm_md5': password_md5}) as resp:
                try:
                    userid = resp.cookies.get("bb_userid").value
                except AttributeError:
                    return False
        return userid

    @staticmethod
    async def forum_display_qserach(name_startsWith: str) -> List[Dict]:
        '''Search for a forum with name that starts with a given string.
        Returns list of the results(empty list in case that nothing was found)
        Each item contains the following:
        title_clean = the title of the forum
        forumid = the id of the forum
        description_clean = the description of the forum
        imageid = the id of the forum image
        lastthread = the title of the last thread in the forum
        lastthreadid = the id of the last thread in the forum
        '''
        session = aiohttp.ClientSession()
        async with session.get("https://www.fxp.co.il/ajax.php", params={
            'do': 'forumdisplayqserach',
                'name_startsWith': name_startsWith}) as resp:
            results = json.loads(await resp.text())
        await session.close()
        return results

    @staticmethod
    async def user_search(fragment: str) -> List[Dict]:
        '''Looking for a user whose name starts with given parameter.
        Returns a list of dictionaries with the results:
        username = <span> tag of the username
        userid = the userid
        usernamenormal = username without Html
        profilepic = Partial link to the profile picture (0 If there is no picture)
        '''
        session = aiohttp.ClientSession()
        async with session.post("https://www.fxp.co.il/ajax.php", data={
            # Until now I have not come across a case where being connected
            # changed the result, so I preferred to make this function static.
            'securitytoken': 'guest',
            'do': 'usersearch_json',
                'fragment': fragment}) as resp:
            results = json.loads(await resp.text())
        await session.close()
        return results

class vBulletin:
    @staticmethod
    async def editor_switch(message: str, towysiwyg: Optional[bool] = False, parsetype: Optional[str] = '21') -> str:
        '''Turns vBulletin into HTML and vice versa!

        Parameters:
        message(str): The message you want to "switch".
        towysiwyg(bool) [Optional]: Convert to html(True) or to vBulletin(False)?
        parsetype(str) [Optional]: In which forum will the message will be converted?
        
        Returns:
        (str): The converted message'''
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://www.fxp.co.il/ajax.php", data={
                'do': 'editorswitch',
                'allowsmilie': '1',
                'parsetype': parsetype,
                'message': message,
                'towysiwyg' : towysiwyg}) as resp:
                    return ElementTree.fromstring(await resp.text()).text
            
class Emails:
    ''' Bonus! An easy way to authenticate users. '''
    @staticmethod
    async def Generate_Email() -> str:
        ''' Returns an email with which you will register. '''
        async with aiohttp.ClientSession() as session:
            async with session.post("https://gmailnator.com/index/indexquery", data={"action": "GenerateEmail", "data[]": "3"}) as resp:
                return await resp.text()

    @staticmethod
    async def verify_email(email: str, retry: Optional[int] = 5) -> bool:
        ''' Verifies your email. Note that this is only available for emails created using Generate_Email ().

        Parameters:
        email (str): The email you want to verify
        retry (int) [Optional]: The number of times you want to try again'''
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://gmailnator.com/mailbox/mailboxquery", data={"action": "LoadMailList", "Email_address": email}) as resp:
                    code = re.search(r"<a href=\\\"(.*?)\">", await resp.text()).group(1).split("\\")
                    async with session.post("https://gmailnator.com/mailbox/get_single_message/", data={"action": "get_message", "message_id": code[5][2:], "email": code[3][1:]}) as response:
                        code = re.search(r"<a href=\"(.*?)\"", await response.text()).group(1)
                        await session.get(code)
                        return True
        except BaseException:
            # If you've tried to verify before the email arrives, try waiting
            # and checking again.
            if retry == 0:
                return False
            await asyncio.sleep(5)
            return await Emails.verify_email(email, retry - 1)


#### adding events that doesn't require specific forum ####
for event in (
    "newpmonpage",
    "new_like",
    "newpm",
    "newreply",
    "online_update",
        "posts_update"):
    def tmp(self, func, event=event):
        async def wrapper(*args, **kwargs):
            @self.sio.on(event)
            async def call(data):
                await func(obj(**data))
        self.wrappers.append(wrapper())
        return wrapper
    tmp.__doc__ = f"Activates the decorated function when {event} is triggered\nReturns an object with the returned information"
    setattr(FxP, "on_" + event, tmp)

#### adding events that require connection to a thread / forum ####
for event in (("update_post", FxP.FORUM), ("showthreadpost", FxP.THREAD)):
    def tmp(self, thread_id, event=event):
        def decorator(func):
            async def wrapper(*args, **kwargs):
                if await self._connect(thread_id, event[1]):
                    @self.sio.on(event[0])
                    async def call(data):
                        await func(obj(**data))
                else:
                    raise ConnectionFailed()
            self.wrappers.append(wrapper())
            return wrapper
        return decorator
    setattr(FxP, "on_" + event[0], tmp)


if __name__ == '__main__':
    management = [line.rstrip('\n') for line in open("management.txt")]
    bot = FxP("Dzez", "18112004")

    @bot.on_new_thread('21')
    async def do_smt(thread):
        if thread.username in management:
            return
        content = await thread.content()
        title = thread.title
        thread_id = await bot.post_thread('67', title, content + f"<br>אשכול נפתח על ידי: [taguser]{thread.poster}[/taguser]")
        print("Posted a new thread, id =", thread_id)

    @bot.on_newpmonpage
    async def on_new_pm(data):
        if data.username == bot.username:
            return
        
        if data.messagelist == "הסר":
            if data.username in management:
                await bot.send_pm("אתה כבר לא במערכת!!!", data.parentpmid_node, data.username)
                return
            management.append(data.username)
            with open("management.txt", "a") as file_object:
                file_object.write("\n" + data.username)
            await bot.send_pm("הוסרת בהצלחה מהמערכת!", data.parentpmid_node, data.username)
            print("Blocked user:", data.username)
            
    #async def main():  
        #for i in range(1, 101):
        #    bot = FxP("קח_לייק" + str(i), "12345678")
        #    await bot._login()
        #    await bot.add_like('206977100')
  
    #asyncio.run(main())
    bot.run()
