#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import g, jsonify, request
from flask_httpauth import HTTPBasicAuth
from flask_restful import Resource
from sqlalchemy import or_

from back import setting
from back.models import User
from . import api_bp
from .errors import unauthorized, forbidden
from .utils import jsonify_with_args

auth = HTTPBasicAuth()


class Auth(Resource):
    """
    参考：https://www.cnblogs.com/vovlie/p/4182814.html
    https://www.cnblogs.com/PyKK2019/p/10889094.html
    """

    def __init__(self):
        self.response_obj = {'success': True, 'code': 0, 'data': None, 'msg': ''}

    def post(self):
        args = request.json
        username = args.get('account') or args.get('authToken')
        password = args.get('password')
        verify_passed = verify_password(username, password)
        if verify_passed:
            token = g.user.generate_auth_token()
            if token:
                data = dict()
                username = g.user.username
                data['Oauth-Token'] = token.decode('ascii')
                data['username'] = username
                self.response_obj['data'] = data
                return jsonify_with_args(self.response_obj)
        else:
            self.response_obj['code'] = 1
            self.response_obj['success'] = False
            self.response_obj['msg'] = 'UNAUTHORIZED'
            return jsonify_with_args(self.response_obj, 401)

    @auth.login_required
    def get(self):
        """
        /api/token 接口
        :return:
        """
        token = g.user.generate_auth_token()
        return jsonify({'token': token.decode('ascii')})


class ResetPassword(Resource):
    """
    重置密码
    """

    def __init__(self):
        self.response_obj = {'success': True, 'code': 0, 'data': None, 'msg': ''}

    def post(self):
        # TODO: 状态码不应该在body中  这个是更新，不应该用POST方法！！！
        data = request.json
        # data = json.loads(str(request.data, encoding="utf-8"))
        user = User.query.filter_by(name=setting.LOGINUSER).first()
        if user and user.verify_user_password(data['oldpass']) and data['confirpass'] == data['newpass']:
            user.hash_password(data['newpass'])
            return jsonify({'code': 0, 'msg': "密码修改成功"})
        else:
            self.response_obj['code'] = 1
            self.response_obj['msg'] = 'Please check args.'
            return jsonify_with_args(jsonify(self.response_obj), 400)

    @auth.login_required
    def get(self):
        """
        # 已注册用户访问该页面
        curl -u admin:123456 -i -X GET http://127.0.0.1:5000/api/password

        首先获取token:
        curl -u admin:123456 -i -X GET http://127.0.0.1:5000/api/token
        然后根据token访问页面：
        curl -u [token]:findpwd -i -X GET http://127.0.0.1:5000/api/password
        """
        username = g.user.username
        return jsonify({'msg': f'Hello, {username}! You have the right to reset password.',
                        'data': username})


@auth.verify_password
def verify_password(account_or_token, password):
    """
    回调函数，验证用户名和密码，if -> True，else False
    :param account_or_token:账号（用户名|邮箱）或者token
    :param password:密码
    :return:
    """
    if not account_or_token:
        return False
    # account_or_token = re.sub(r'^"|"$', '', account_or_token)
    user = User.verify_auth_token(account_or_token)
    if not user:
        user = User.query.filter(or_(User.username == account_or_token, User.email == account_or_token)).first()
        if not user or not user.verify_user_password(password):
            return False
    # user对像会被存储到Flask的g对象中
    g.user = user
    return True


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api_bp.before_request
@auth.login_required
def before_request():
    """
    想要在API访问前加login_required监护。
    为了让api蓝本中的所有API都一次性加上监护，可以用before_request修饰器应用到整个蓝本
    :return:
    """
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden('Unconfirmed account')
