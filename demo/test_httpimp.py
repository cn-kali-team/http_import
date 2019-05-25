import httpimp

KT = httpimp.KTModuleLoader()
sub_modele = KT.load_module('sub.py')
sub_modele.main('bilibili.com')