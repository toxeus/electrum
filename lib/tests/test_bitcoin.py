import base64
import unittest
import sys
from ecdsa.util import number_to_string

from lib.bitcoin import (
    generator_secp256k1, point_to_ser, public_key_to_p2pkh, EC_KEY,
    bip32_root, bip32_public_derivation, bip32_private_derivation, pw_encode,
    pw_decode, Hash, public_key_from_private_key, address_from_private_key,
    is_address, is_private_key, xpub_from_xprv, is_new_seed, is_old_seed,
    var_int, op_push, address_to_script, regenerate_key,
    verify_message, deserialize_privkey, serialize_privkey, is_segwit_address,
    is_b58_address, address_to_scripthash, is_minikey, is_compressed, is_xpub,
    xpub_type, is_xprv, is_bip32_derivation, seed_type, EncodeBase58Check)
from lib.util import bfh
from lib import constants

from . import TestCaseForTestnet


try:
    import ecdsa
except ImportError:
    sys.exit("Error: python-ecdsa does not seem to be installed. Try 'sudo pip install ecdsa'")


class Test_bitcoin(unittest.TestCase):

    def test_crypto(self):
        for message in [b"Chancellor on brink of second bailout for banks", b'\xff'*512]:
            self._do_test_crypto(message)

    def _do_test_crypto(self, message):
        G = generator_secp256k1
        _r  = G.order()
        pvk = ecdsa.util.randrange( pow(2,256) ) %_r

        Pub = pvk*G
        pubkey_c = point_to_ser(Pub,True)
        #pubkey_u = point_to_ser(Pub,False)
        addr_c = public_key_to_p2pkh(pubkey_c)

        #print "Private key            ", '%064x'%pvk
        eck = EC_KEY(number_to_string(pvk,_r))

        #print "Compressed public key  ", pubkey_c.encode('hex')
        enc = EC_KEY.encrypt_message(message, pubkey_c)
        dec = eck.decrypt_message(enc)
        self.assertEqual(message, dec)

        #print "Uncompressed public key", pubkey_u.encode('hex')
        #enc2 = EC_KEY.encrypt_message(message, pubkey_u)
        dec2 = eck.decrypt_message(enc)
        self.assertEqual(message, dec2)

        signature = eck.sign_message(message, True)
        #print signature
        EC_KEY.verify_message(eck, signature, message)

    def test_msg_signing(self):
        msg1 = b'Chancellor on brink of second bailout for banks'
        msg2 = b'Electrum'

        def sign_message_with_wif_privkey(wif_privkey, msg):
            txin_type, privkey, compressed = deserialize_privkey(wif_privkey)
            key = regenerate_key(privkey)
            return key.sign_message(msg, compressed)

        sig1 = sign_message_with_wif_privkey(
            'N5acUJ3Bpizm13gSq8jV5CwZUgfrjs53RuBASsT9AtuwjAgetARW', msg1)
        addr1 = '6iRgFB4Fi922TqJHD7KaFn8Y1DJRHNy9BL'
        sig2 = sign_message_with_wif_privkey(
            '5mBCYSLtLsBez8Dtr83svFzHU1buS7WA6rYGHBfNPFacPfYWwuT', msg2)
        addr2 = '6u7jGyiAQje3RAhBiwZ3pDMKkYCRXuLu76'

        sig1_b64 = base64.b64encode(sig1)
        sig2_b64 = base64.b64encode(sig2)

        self.assertEqual(sig1_b64, b'IMJ177QE+PonT9RcqHL5/aFjo635kMmE6sDi9PAtvqm1PaqCVU16L0Mb3d64z7nNnrDpVWa+2UqaQ1r2oqEkgsE=')
        self.assertEqual(sig2_b64, b'HOrxiXh8D4ddJSG2x3oV7OVYSOC45DuLst/uS+G3tc70OZyuqet67q1r+7fKDXEBkhTSXbt+gl+iC7/okXLXYec=')

        self.assertTrue(verify_message(addr1, sig1, msg1))
        self.assertTrue(verify_message(addr2, sig2, msg2))

        self.assertFalse(verify_message(addr1, b'wrong', msg1))
        self.assertFalse(verify_message(addr1, sig2, msg1))

    def test_aes_homomorphic(self):
        """Make sure AES is homomorphic."""
        payload = u'\u66f4\u7a33\u5b9a\u7684\u4ea4\u6613\u5e73\u53f0'
        password = u'secret'
        enc = pw_encode(payload, password)
        dec = pw_decode(enc, password)
        self.assertEqual(dec, payload)

    def test_aes_encode_without_password(self):
        """When not passed a password, pw_encode is noop on the payload."""
        payload = u'\u66f4\u7a33\u5b9a\u7684\u4ea4\u6613\u5e73\u53f0'
        enc = pw_encode(payload, None)
        self.assertEqual(payload, enc)

    def test_aes_deencode_without_password(self):
        """When not passed a password, pw_decode is noop on the payload."""
        payload = u'\u66f4\u7a33\u5b9a\u7684\u4ea4\u6613\u5e73\u53f0'
        enc = pw_decode(payload, None)
        self.assertEqual(payload, enc)

    def test_aes_decode_with_invalid_password(self):
        """pw_decode raises an Exception when supplied an invalid password."""
        payload = u"blah"
        password = u"uber secret"
        wrong_password = u"not the password"
        enc = pw_encode(payload, password)
        self.assertRaises(Exception, pw_decode, enc, wrong_password)

    def test_hash(self):
        """Make sure the Hash function does sha256 twice"""
        payload = u"test"
        expected = b'\x95MZI\xfdp\xd9\xb8\xbc\xdb5\xd2R&x)\x95\x7f~\xf7\xfalt\xf8\x84\x19\xbd\xc5\xe8"\t\xf4'

        result = Hash(payload)
        self.assertEqual(expected, result)

    def test_var_int(self):
        for i in range(0xfd):
            self.assertEqual(var_int(i), "{:02x}".format(i) )

        self.assertEqual(var_int(0xfd), "fdfd00")
        self.assertEqual(var_int(0xfe), "fdfe00")
        self.assertEqual(var_int(0xff), "fdff00")
        self.assertEqual(var_int(0x1234), "fd3412")
        self.assertEqual(var_int(0xffff), "fdffff")
        self.assertEqual(var_int(0x10000), "fe00000100")
        self.assertEqual(var_int(0x12345678), "fe78563412")
        self.assertEqual(var_int(0xffffffff), "feffffffff")
        self.assertEqual(var_int(0x100000000), "ff0000000001000000")
        self.assertEqual(var_int(0x0123456789abcdef), "ffefcdab8967452301")

    def test_op_push(self):
        self.assertEqual(op_push(0x00), '00')
        self.assertEqual(op_push(0x12), '12')
        self.assertEqual(op_push(0x4b), '4b')
        self.assertEqual(op_push(0x4c), '4c4c')
        self.assertEqual(op_push(0xfe), '4cfe')
        self.assertEqual(op_push(0xff), '4cff')
        self.assertEqual(op_push(0x100), '4d0001')
        self.assertEqual(op_push(0x1234), '4d3412')
        self.assertEqual(op_push(0xfffe), '4dfeff')
        self.assertEqual(op_push(0xffff), '4dffff')
        self.assertEqual(op_push(0x10000), '4e00000100')
        self.assertEqual(op_push(0x12345678), '4e78563412')

    def test_address_to_script(self):
        # bech32 native segwit
        # test vectors from BIP-0173, adapted for Feathercoin
        self.assertEqual(address_to_script('FC1QMK84YX50TRP37UL4SYLFG3SH4CV5RCVWY9AJUK'), '0014dd8f521a8f58c31f73f5813e944617ae1941e18e')
        self.assertEqual(address_to_script('fc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7k34wt34'), '5128751e76e8199196d454941c45d1b3a323f1433bd6751e76e8199196d454941c45d1b3a323f1433bd6')
        self.assertEqual(address_to_script('fc1sw50qvkz623'), '6002751e')
        self.assertEqual(address_to_script('fc1zw508d6qejxtdg4y5r3zarvaryvgqhvh8'), '5210751e76e8199196d454941c45d1b3a323')

        # base58 P2PKH
        self.assertEqual(address_to_script('6hR4DL6rgjHYCGKQ4o4eigvfgrirgGNrsS'), '76a91428662c67561b95c79d2257d2a93d9d151c977e9188ac')
        self.assertEqual(address_to_script('6oyHTWs6UaVFnspscabTxdec3P6hx8gmo1'), '76a914704f4b81cadb7bf7e68c08cd3657220f680f863c88ac')

        # base58 P2SH
        self.assertEqual(address_to_script('35ZqQJcBQMZ1rsv8aSuJ2wkC7ohUCQMJbT'), 'a9142a84cf00d47f699ee7bbc1dea5ec1bdecb4ac15487')
        self.assertEqual(address_to_script('3PyjzJ3im7f7bcV724GR57edKDqoZvH7Ji'), 'a914f47c8954e421031ad04ecd8e7752c9479206b9d387')


class Test_bitcoin_testnet(TestCaseForTestnet):

    def test_address_to_script(self):
        # bech32 native segwit
        # test vectors from BIP-0173, adapted for Feathercoin
        self.assertEqual(address_to_script('tf1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qtmut5m'), '00201863143c14c5166804bd19203356da136c985678cd4d27a1b8c6329604903262')
        self.assertEqual(address_to_script('tf1qqqqqp399et2xygdj5xreqhjjvcmzhxw4aywxecjdzew6hylgvses8d594p'), '0020000000c4a5cad46221b2a187905e5266362b99d5e91c6ce24d165dab93e86433')

        # base58 P2PKH
        self.assertEqual(address_to_script('mutXcGt1CJdkRvXuN2xoz2quAAQYQ59bRX'), '76a9149da64e300c5e4eb4aaffc9c2fd465348d5618ad488ac')
        self.assertEqual(address_to_script('miqtaRTkU3U8rzwKbEHx3g8FSz8GJtPS3K'), '76a914247d2d5b6334bdfa2038e85b20fc15264f8e5d2788ac')

        # base58 P2SH
        self.assertEqual(address_to_script('2N3LSvr3hv5EVdfcrxg2Yzecf3SRvqyBE4p'), 'a9146eae23d8c4a941316017946fc761a7a6c85561fb87')
        self.assertEqual(address_to_script('2NE4ZdmxFmUgwu5wtfoN2gVniyMgRDYq1kk'), 'a914e4567743d378957cd2ee7072da74b1203c1a7a0b87')


class Test_xprv_xpub(unittest.TestCase):

    xprv_xpub = (
        # Taken from test vectors in https://en.bitcoin.it/wiki/BIP_0032_TestVectors
        {'xprv': 'xqMPAnwzqh1qiKsaPeqAMNG26hoV5gXquHoVx4WdsfKxstRoKonobEztp3FSNyE3JZki4rMcnmWMLwbxArNVb5P9Depi8dvKYBmW8DG1bFPqwz1',
         'xpub': 'xq1voqNse7SRu45ADnQmvZVPZqtBy9aXcp1ceqL7rgvNXENXPaaQBH1ZNqJHwLToctYN2mugJWWN49RMc9wdqaEVxrNFRozyozUsJX31ijBpm9t',
         'xtype': 'standard'},
        {'xprv': 'yprvAJEYHeNEPcyBoQYM7sGCxDiNCTX65u4ANgZuSGTrKN5YCC9MP84SBayrgaMyZV7zvkHrr3HVPTK853s2SPk4EttPazBZBmz6QfDkXeE8Zr7',
         'xpub': 'ypub6XDth9u8DzXV1tcpDtoDKMf6kVMaVMn1juVWEesTshcX4zUVvfNgjPJLXrD9N7AdTLnbHFL64KmBn3SNaTe69iZYbYCqLCCNPZKbLz9niQ4',
         'xtype': 'p2wpkh-p2sh'},
        {'xprv': 'zprvAWgYBBk7JR8GkraNZJeEodAp2UR1VRWJTXyV1ywuUVs1awUgTiBS1ZTDtLA5F3MFDn1LZzu8dUpSKdT7ToDpvEG6PQu4bJs7zQY47Sd3sEZ',
         'xpub': 'zpub6jftahH18ngZyLeqfLBFAm7YaWFVttE9pku5pNMX2qPzTjoq1FVgZMmhjecyB2nqFb31gHE9vNvbaggU6vvWpNZbXEWLLUjYjFqG95LNyT8',
         'xtype': 'p2wpkh'},
    )

    def _do_test_bip32(self, seed, sequence):
        xprv, xpub = bip32_root(bfh(seed), 'standard')
        self.assertEqual("m/", sequence[0:2])
        path = 'm'
        sequence = sequence[2:]
        for n in sequence.split('/'):
            child_path = path + '/' + n
            if n[-1] != "'":
                xpub2 = bip32_public_derivation(xpub, path, child_path)
            xprv, xpub = bip32_private_derivation(xprv, path, child_path)
            if n[-1] != "'":
                self.assertEqual(xpub, xpub2)
            path = child_path

        return xpub, xprv

    def test_bip32(self):
        # see https://en.bitcoin.it/wiki/BIP_0032_TestVectors
        xpub, xprv = self._do_test_bip32("000102030405060708090a0b0c0d0e0f", "m/0'/1/2'/2/1000000000")
        self.assertEqual("xq1vp2NrCFqqPVyofcGtRDjLssVtMVqwpx1dUDo8SgsFz6sGaV8o2ARkXgBhgcccMVdmooRys3VyMVaq6zhsjqcuWADuD24HScjh31bxS8W5kiZ", xpub)
        self.assertEqual("xqMPAywyPqRFCmnDqUhGr2VyQjRBU2oG7RoWmSyeTfGrLkvYWiMCS8R5xt8r8FFS1CzfJvbr4N4hccGVtLyXtcSJgqZJhHtQHBSGT99DtryXkpW", xprv)

        xpub, xprv = self._do_test_bip32("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542","m/0/2147483647'/1/2147483646'/2")
        self.assertEqual("xq1vp19iSrHi4BeV39SucQLG9S7uWKZV4nTkcEe8JTtqrrmj8DLuRJchUdz4huC4sCu4WQyqJTHxDCH5hccmdMa7cvHpXNPP8q1U8YVoMZgETkj", xpub)
        self.assertEqual("xqMPAxiqeRs7sTSuD1sJ3D6tgJ3CcrWoMGFduTpeKSJSDWq14SZJqGc2uqwD9YSc1jc7QuDPegXyyZhwPjdkRQBrYMU1gB8vVc5d2x4PAJ7yCcs", xprv)

    def test_xpub_from_xprv(self):
        """We can derive the xpub key from a xprv."""
        for xprv_details in self.xprv_xpub:
            result = xpub_from_xprv(xprv_details['xprv'])
            self.assertEqual(result, xprv_details['xpub'])

    def test_is_xpub(self):
        for xprv_details in self.xprv_xpub:
            xpub = xprv_details['xpub']
            self.assertTrue(is_xpub(xpub))
        self.assertFalse(is_xpub('xpub1nval1d'))
        self.assertFalse(is_xpub('xpub661MyMwAqRbcFWohJWt7PHsFEJfZAvw9ZxwQoDa4SoMgsDDM1T7WK3u9E4edkC4ugRnZ8E4xDZRpk8Rnts3Nbt97dPwT52WRONGBADWRONG'))

    def test_xpub_type(self):
        for xprv_details in self.xprv_xpub:
            xpub = xprv_details['xpub']
            self.assertEqual(xprv_details['xtype'], xpub_type(xpub))

    def test_is_xprv(self):
        for xprv_details in self.xprv_xpub:
            xprv = xprv_details['xprv']
            self.assertTrue(is_xprv(xprv))
        self.assertFalse(is_xprv('xprv1nval1d'))
        self.assertFalse(is_xprv('xprv661MyMwAqRbcFWohJWt7PHsFEJfZAvw9ZxwQoDa4SoMgsDDM1T7WK3u9E4edkC4ugRnZ8E4xDZRpk8Rnts3Nbt97dPwT52WRONGBADWRONG'))

    def test_is_bip32_derivation(self):
        self.assertTrue(is_bip32_derivation("m/0'/1"))
        self.assertTrue(is_bip32_derivation("m/0'/0'"))
        self.assertTrue(is_bip32_derivation("m/44'/0'/0'/0/0"))
        self.assertTrue(is_bip32_derivation("m/49'/0'/0'/0/0"))
        self.assertFalse(is_bip32_derivation("mmmmmm"))
        self.assertFalse(is_bip32_derivation("n/"))
        self.assertFalse(is_bip32_derivation(""))
        self.assertFalse(is_bip32_derivation("m/q8462"))

    def test_version_bytes(self):
        xprv_headers_b58 = {
            'standard':    'xqMP',
            'p2wpkh-p2sh': 'yprv',
            'p2wsh-p2sh':  'Yprv',
            'p2wpkh':      'zprv',
            'p2wsh':       'Zprv',
        }
        xpub_headers_b58 = {
            'standard':    'xq1v',
            'p2wpkh-p2sh': 'ypub',
            'p2wsh-p2sh':  'Ypub',
            'p2wpkh':      'zpub',
            'p2wsh':       'Zpub',
        }
        for xtype, xkey_header_bytes in constants.net.XPRV_HEADERS.items():
            xkey_header_bytes = bfh("%08x" % xkey_header_bytes)
            xkey_bytes = xkey_header_bytes + bytes([0] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xprv_headers_b58[xtype]))

            xkey_bytes = xkey_header_bytes + bytes([255] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xprv_headers_b58[xtype]))

        for xtype, xkey_header_bytes in constants.net.XPUB_HEADERS.items():
            xkey_header_bytes = bfh("%08x" % xkey_header_bytes)
            xkey_bytes = xkey_header_bytes + bytes([0] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xpub_headers_b58[xtype]))

            xkey_bytes = xkey_header_bytes + bytes([255] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xpub_headers_b58[xtype]))


class Test_xprv_xpub_testnet(TestCaseForTestnet):

    def test_version_bytes(self):
        xprv_headers_b58 = {
            'standard':    'tprv',
            'p2wpkh-p2sh': 'uprv',
            'p2wsh-p2sh':  'Uprv',
            'p2wpkh':      'vprv',
            'p2wsh':       'Vprv',
        }
        xpub_headers_b58 = {
            'standard':    'tpub',
            'p2wpkh-p2sh': 'upub',
            'p2wsh-p2sh':  'Upub',
            'p2wpkh':      'vpub',
            'p2wsh':       'Vpub',
        }
        for xtype, xkey_header_bytes in constants.net.XPRV_HEADERS.items():
            xkey_header_bytes = bfh("%08x" % xkey_header_bytes)
            xkey_bytes = xkey_header_bytes + bytes([0] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xprv_headers_b58[xtype]))

            xkey_bytes = xkey_header_bytes + bytes([255] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xprv_headers_b58[xtype]))

        for xtype, xkey_header_bytes in constants.net.XPUB_HEADERS.items():
            xkey_header_bytes = bfh("%08x" % xkey_header_bytes)
            xkey_bytes = xkey_header_bytes + bytes([0] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xpub_headers_b58[xtype]))

            xkey_bytes = xkey_header_bytes + bytes([255] * 74)
            xkey_b58 = EncodeBase58Check(xkey_bytes)
            self.assertTrue(xkey_b58.startswith(xpub_headers_b58[xtype]))


class Test_keyImport(unittest.TestCase):

    priv_pub_addr = (
           {'priv': 'N77oHMwqXeMvcq4N7PGBiuD1QJBjHD2L2sRRNmmYyJWWaPhLzuQn',
            'exported_privkey': 'N77oHMwqXeMvcq4N7PGBiuD1QJBjHD2L2sRRNmmYyJWWaPhLzuQn',
            'pub': '023a081e220b983d8418899c354defdd644575581913dad327aa205d129fb3f519',
            'address': '6oLWMBechqxE98A7opVvPe1HkTaxCkANip',
            'minikey' : False,
            'txin_type': 'p2pkh',
            'compressed': True,
            'addr_encoding': 'base58',
            'scripthash': 'b961469efb2ada5cafd2b2911e4341f7f263b917bf6fbf446ca80eca1558f35b'},
           {'priv': 'p2pkh:Kzj8VjwpZ99bQqVeUiRXrKuX9mLr1o6sWxFMCBJn1umC38BMiQTD',
            'exported_privkey': 'N4qxVzzR1HyX45gQDmx2zmELdr9yheu3o8yB2YA6tcK9yktRVSLV',
            'pub': '0352d78b4b37e0f6d4e164423436f2925fa57817467178eca550a88f2821973c41',
            'address': '6uG8Lbak3DFnuMSfAM428isDX6PoYy6zVk',
            'minikey': False,
            'txin_type': 'p2pkh',
            'compressed': True,
            'addr_encoding': 'base58',
            'scripthash': 'a9b2a76fc196c553b352186dfcca81fcf323a721cd8431328f8e9d54216818c1'},
           {'priv': '5mtucV3Ey9rVFBhSqpLJ3ZYHjXJP2kgMNXaEiAC6Mo2PaqgN3t9',
            'exported_privkey': '5mtucV3Ey9rVFBhSqpLJ3ZYHjXJP2kgMNXaEiAC6Mo2PaqgN3t9',
            'pub': '04d4febb2ae001a037360ebb6d202614769e39a3bcb36e3d87f031a35b06effe81729e92d18aded783ecee9ca315231614e067a8540b7197de0555265145be1d03',
            'address': '6sgmAodqVZrFACLBBsxx67f33Ze8KDJrJd',
            'minikey': False,
            'txin_type': 'p2pkh',
            'compressed': False,
            'addr_encoding': 'base58',
            'scripthash': '322092a15881322cc38db6b5c0a354a7bfbbb2fe26c414d3903b0da7f5a1756c'},
           {'priv': 'p2pkh:5KhYQCe1xd5g2tqpmmGpUWDpDuTbA8vnpbiCNDwMPAx29WNQYfN',
            'exported_privkey': '5nuxsSvTtaYqvNyhTsxopzcf3W5eFzj3qYhhnKZuJM3T4DQTa6a',
            'pub': '048f0431b0776e8210376c81280011c2b68be43194cb00bd47b7e9aa66284b713ce09556cde3fee606051a07613f3c159ef3953b8927c96ae3dae94a6ba4182e0e',
            'address': '6grCVwTKhgA76RMf2iKXXntYoy7YJ21vf1',
            'minikey': False,
            'txin_type': 'p2pkh',
            'compressed': False,
            'addr_encoding': 'base58',
            'scripthash': '6dd2e07ad2de9ba8eec4bbe8467eb53f8845acff0d9e6f5627391acc22ff62df'},
           {'priv': 'LHJnnvRzsdrTX2j5QeWVsaBkabK7gfMNqNNqxnbBVRaJYfk24iJz',
            'exported_privkey': 'LHJnnvRzsdrTX2j5QeWVsaBkabK7gfMNqNNqxnbBVRaJYfk24iJz',
            'pub': '0279ad237ca0d812fb503ab86f25e15ebd5fa5dd95c193639a8a738dcd1acbad81',
            'address': '3GeVJB3oKr7psgKR6BTXSxKtWUkfsHHhk7',
            'minikey': False,
            'txin_type': 'p2wpkh-p2sh',
            'compressed': True,
            'addr_encoding': 'base58',
            'scripthash': 'd7b04e882fa6b13246829ac552a2b21461d9152eb00f0a6adb58457a3e63d7c5'},
           {'priv': 'p2wpkh-p2sh:L3CZH1pm87X4bbE6mSGvZnAZ1KcFDRomBudUkrkBG7EZhDtBVXMW',
            'exported_privkey': 'LLMpRLYZURMLYdFdsb4iA8MXWC1YtGMDWnsjsmSNF4jzFtGcPc4N',
            'pub': '0229da20a15b3363b2c28e3c5093c180b56c439df0b968a970366bb1f38435361e',
            'address': '3C79goMwT7zSTjXnPoCg6VFGAnUpZAkyus',
            'minikey': False,
            'txin_type': 'p2wpkh-p2sh',
            'compressed': True,
            'addr_encoding': 'base58',
            'scripthash': '714bf6bfe1083e69539f40d4c7a7dca85d187471b35642e55f20d7e866494cf7'},
           {'priv': 'L8g5V8kFFeg2WbecahRSdobARbHz2w2STH9S8ePHVSY4fmia7Rsj',
            'exported_privkey': 'L8g5V8kFFeg2WbecahRSdobARbHz2w2STH9S8ePHVSY4fmia7Rsj',
            'pub': '03e9f948421aaa89415dc5f281a61b60dde12aae3181b3a76cd2d849b164fc6d0b',
            'address': 'fc1qqmpt7u5e9hfznljta5gnvhyvfd2kdd0rlt95uc',
            'minikey': False,
            'txin_type': 'p2wpkh',
            'compressed': True,
            'addr_encoding': 'bech32',
            'scripthash': '1929acaaef3a208c715228e9f1ca0318e3a6b9394ab53c8d026137f847ecf97b'},
           {'priv': 'p2wpkh:KyDWy5WbjLA58Zesh1o8m3pADGdJ3v33DKk4m7h8BD5zDKDmDFwo',
            'exported_privkey': 'L7o9YEsVuV5D75feF6C2ZDueThpwtLJmNmNCKa3DfgqhVeNyp5AU',
            'pub': '038c57657171c1f73e34d5b3971d05867d50221ad94980f7e87cbc2344425e6a1e',
            'address': 'fc1qpakeeg4d9ydyjxd8paqrw4xy9htsg532ux5f5w',
            'minikey': False,
            'txin_type': 'p2wpkh',
            'compressed': True,
            'addr_encoding': 'bech32',
            'scripthash': '242f02adde84ebb2a7dd778b2f3a81b3826f111da4d8960d826d7a4b816cb261'},
           # from http://bitscan.com/articles/security/spotlight-on-mini-private-keys
           {'priv': 'SzavMBLoXU6kDrqtUVmffv',
            'exported_privkey': 'N9AVCYp19kCjeRF4TtBh36y73MvjraQAYLX8qWNzaxYvEJuKU78z',
            'pub': '02588d202afcc1ee4ab5254c7847ec25b9a135bbda0f2bc69ee1a714749fd77dc9',
            'address': '6n1Mhk6PJ13QNu5HHKmcTgbwWREHGqF1sV',
            'minikey': True,
            'txin_type': 'p2pkh',
            'compressed': True,  # this is actually ambiguous... issue #2748
            'addr_encoding': 'base58',
            'scripthash': '60ad5a8b922f758cd7884403e90ee7e6f093f8d21a0ff24c9a865e695ccefdf1'},
    )

    def test_public_key_from_private_key(self):
        for priv_details in self.priv_pub_addr:
            txin_type, privkey, compressed = deserialize_privkey(priv_details['priv'])
            result = public_key_from_private_key(privkey, compressed)
            self.assertEqual(priv_details['pub'], result)
            self.assertEqual(priv_details['txin_type'], txin_type)
            self.assertEqual(priv_details['compressed'], compressed)

    def test_address_from_private_key(self):
        for priv_details in self.priv_pub_addr:
            addr2 = address_from_private_key(priv_details['priv'])
            self.assertEqual(priv_details['address'], addr2)

    def test_is_valid_address(self):
        for priv_details in self.priv_pub_addr:
            addr = priv_details['address']
            self.assertFalse(is_address(priv_details['priv']))
            self.assertFalse(is_address(priv_details['pub']))
            self.assertTrue(is_address(addr))

            is_enc_b58 = priv_details['addr_encoding'] == 'base58'
            self.assertEqual(is_enc_b58, is_b58_address(addr))

            is_enc_bech32 = priv_details['addr_encoding'] == 'bech32'
            self.assertEqual(is_enc_bech32, is_segwit_address(addr))

        self.assertFalse(is_address("not an address"))

    def test_is_private_key(self):
        for priv_details in self.priv_pub_addr:
            self.assertTrue(is_private_key(priv_details['priv']))
            self.assertTrue(is_private_key(priv_details['exported_privkey']))
            self.assertFalse(is_private_key(priv_details['pub']))
            self.assertFalse(is_private_key(priv_details['address']))
        self.assertFalse(is_private_key("not a privkey"))

    def test_serialize_privkey(self):
        for priv_details in self.priv_pub_addr:
            txin_type, privkey, compressed = deserialize_privkey(priv_details['priv'])
            priv2 = serialize_privkey(privkey, compressed, txin_type)
            self.assertEqual(priv_details['exported_privkey'], priv2)

    def test_address_to_scripthash(self):
        for priv_details in self.priv_pub_addr:
            sh = address_to_scripthash(priv_details['address'])
            self.assertEqual(priv_details['scripthash'], sh)

    def test_is_minikey(self):
        for priv_details in self.priv_pub_addr:
            minikey = priv_details['minikey']
            priv = priv_details['priv']
            self.assertEqual(minikey, is_minikey(priv))

    def test_is_compressed(self):
        for priv_details in self.priv_pub_addr:
            self.assertEqual(priv_details['compressed'],
                             is_compressed(priv_details['priv']))


class Test_seeds(unittest.TestCase):
    """ Test old and new seeds. """

    mnemonics = {
        ('cell dumb heartbeat north boom tease ship baby bright kingdom rare squeeze', 'old'),
        ('cell dumb heartbeat north boom tease ' * 4, 'old'),
        ('cell dumb heartbeat north boom tease ship baby bright kingdom rare badword', ''),
        ('cElL DuMb hEaRtBeAt nOrTh bOoM TeAsE ShIp bAbY BrIgHt kInGdOm rArE SqUeEzE', 'old'),
        ('   cElL  DuMb hEaRtBeAt nOrTh bOoM  TeAsE ShIp    bAbY BrIgHt kInGdOm rArE SqUeEzE   ', 'old'),
        # below seed is actually 'invalid old' as it maps to 33 hex chars
        ('hurry idiot prefer sunset mention mist jaw inhale impossible kingdom rare squeeze', 'old'),
        ('cram swing cover prefer miss modify ritual silly deliver chunk behind inform able', 'standard'),
        ('cram swing cover prefer miss modify ritual silly deliver chunk behind inform', ''),
        ('ostrich security deer aunt climb inner alpha arm mutual marble solid task', 'standard'),
        ('OSTRICH SECURITY DEER AUNT CLIMB INNER ALPHA ARM MUTUAL MARBLE SOLID TASK', 'standard'),
        ('   oStRiCh sEcUrItY DeEr aUnT ClImB       InNeR AlPhA ArM MuTuAl mArBlE   SoLiD TaSk  ', 'standard'),
        ('x8', 'standard'),
        ('science dawn member doll dutch real can brick knife deny drive list', '2fa'),
        ('science dawn member doll dutch real ca brick knife deny drive list', ''),
        (' sCience dawn   member doll Dutch rEAl can brick knife deny drive  lisT', '2fa'),
        ('frost pig brisk excite novel report camera enlist axis nation novel desert', 'segwit'),
        ('  fRoSt pig brisk excIte novel rePort CamEra enlist axis nation nOVeL dEsert ', 'segwit'),
        ('9dk', 'segwit'),
    }
    
    def test_new_seed(self):
        seed = "cram swing cover prefer miss modify ritual silly deliver chunk behind inform able"
        self.assertTrue(is_new_seed(seed))

        seed = "cram swing cover prefer miss modify ritual silly deliver chunk behind inform"
        self.assertFalse(is_new_seed(seed))

    def test_old_seed(self):
        self.assertTrue(is_old_seed(" ".join(["like"] * 12)))
        self.assertFalse(is_old_seed(" ".join(["like"] * 18)))
        self.assertTrue(is_old_seed(" ".join(["like"] * 24)))
        self.assertFalse(is_old_seed("not a seed"))

        self.assertTrue(is_old_seed("0123456789ABCDEF" * 2))
        self.assertTrue(is_old_seed("0123456789ABCDEF" * 4))

    def test_seed_type(self):
        for seed_words, _type in self.mnemonics:
            self.assertEqual(_type, seed_type(seed_words), msg=seed_words)
