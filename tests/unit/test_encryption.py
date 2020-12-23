'''This module tests the various classes and functions in the encryption module'''
import json
import os
import shutil
import time

import nacl.signing
from pyanselus.encodedstring import EncodedString
import pyanselus.encryption as encryption
# Pylint doesn't detect the use of this import:
from pyanselus.retval import RetVal # pylint: disable=unused-import

def setup_test(name):
	'''Creates a test folder hierarchy'''
	test_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'testfiles')
	if not os.path.exists(test_folder):
		os.mkdir(test_folder)

	test_folder = os.path.join(test_folder, name)
	while os.path.exists(test_folder):
		try:
			shutil.rmtree(test_folder)
		except:
			print("Waiting a second for test folder to unlock")
			time.sleep(1.0)
	os.mkdir(test_folder)
	return test_folder


def test_encryptionpair_save():
	'''Tests the save code of the EncryptionPair class'''
	test_folder = setup_test('encryption_encryptionpair_save')

	public_key = EncodedString("CURVE25519:(B2XX5|<+lOSR>_0mQ=KX4o<aOvXe6M`Z5ldINd`")
	private_key = EncodedString("CURVE25519:(Rj5)mmd1|YqlLCUP0vE;YZ#o;tJxtlAIzmPD7b&")
	kp = encryption.EncryptionPair(public_key, private_key)

	keypair_path = os.path.join(test_folder, 'testpair.jk')
	status = kp.save(keypair_path)
	assert not status.error(), f"Failed to create saved encryption pair file: {status.info()}"

	fhandle = open(keypair_path)
	filedata = json.load(fhandle)
	fhandle.close()

	assert filedata['PublicKey'] == public_key.as_string(), "Saved data does not match input data"
	assert filedata['PrivateKey'] == private_key.as_string(), "Saved data does not match input data"


def test_encryptionpair_load():
	'''Tests the load code of the EncryptionPair class'''
	test_folder = setup_test('encryption_encryptionpair_load')

	public_key = EncodedString("CURVE25519:(B2XX5|<+lOSR>_0mQ=KX4o<aOvXe6M`Z5ldINd`")
	private_key = EncodedString("CURVE25519:(Rj5)mmd1|YqlLCUP0vE;YZ#o;tJxtlAIzmPD7b&")
	kp = encryption.EncryptionPair(public_key, private_key)

	keypair_path = os.path.join(test_folder, 'testpair.jk')
	status = kp.save(keypair_path)
	assert not status.error(), f"Failed to create saved encryption pair file: {status.info()}"

	status = encryption.load_encryptionpair(keypair_path)
	assert not status.error(), f"Failed to load saved pair file: {status.info()}"

	testpair = status['keypair']

	assert testpair.enctype == kp.enctype, "Loaded data does not match input data"
	assert testpair.public == public_key, "Loaded data does not match input data"
	assert testpair.private == private_key, "Loaded data does not match input data"
	

def test_signpair_save():
	'''Tests the save code of the SigningPair class'''
	test_folder = setup_test('encryption_signpair_save')

	public_key = EncodedString(r"ED25519:PnY~pK2|;AYO#1Z;B%T$2}E$^kIpL=>>VzfMKsDx")
	private_key = EncodedString(r"ED25519:{^A@`5N*T%5ybCU%be892x6%*Rb2rnYd=SGeO4jF")
	sp = encryption.SigningPair(public_key, private_key)

	keypair_path = os.path.join(test_folder, 'testpair.jk')
	status = sp.save(keypair_path)
	assert not status.error(), f"Failed to create saved signing pair file: {status.info()}"

	fhandle = open(keypair_path)
	filedata = json.load(fhandle)
	fhandle.close()

	assert filedata['VerificationKey'] == public_key.as_string(), \
		"Saved data does not match input data"
	assert filedata['SigningKey'] == private_key.as_string(), "Saved data does not match input data"


def test_signpair_load():
	'''Tests the load code of the SigningPair class'''
	test_folder = setup_test('encryption_signpair_load')

	public_key = EncodedString(r"ED25519:PnY~pK2|;AYO#1Z;B%T$2}E$^kIpL=>>VzfMKsDx")
	private_key = EncodedString(r"ED25519:{^A@`5N*T%5ybCU%be892x6%*Rb2rnYd=SGeO4jF")
	kp = encryption.SigningPair(public_key, private_key)

	keypair_path = os.path.join(test_folder, 'testpair.jk')
	status = kp.save(keypair_path)
	assert not status.error(), f"Failed to create saved signing pair file: {status.info()}"

	status = encryption.load_signingpair(keypair_path)
	assert not status.error(), f"Failed to load saved signing pair file: {status.info()}"

	testpair = status['keypair']

	assert testpair.enctype == kp.enctype, "Loaded data does not match input data"
	assert testpair.public == public_key, "Loaded data does not match input data"
	assert testpair.private == private_key, "Loaded data does not match input data"


def test_signpair_sign():
	'''Tests SigningPair's sign() method'''

	public_key = EncodedString(r"ED25519:PnY~pK2|;AYO#1Z;B%T$2}E$^kIpL=>>VzfMKsDx")
	private_key = EncodedString(r"ED25519:{^A@`5N*T%5ybCU%be892x6%*Rb2rnYd=SGeO4jF")
	sp = encryption.SigningPair(public_key, private_key)

	key = nacl.signing.SigningKey(private_key.raw_data())
	signed = key.sign(b'1234567890', encryption.Base85Encoder)
	
	status = sp.sign(b'1234567890')
	assert not status.error(), f"test_signpair_sign failed: {status.info()}"
	assert status['signature'] == 'ED25519:' + signed.signature.decode(), \
		"test_signpair_sign: signature data failed to match"


def test_secretkey_save():
	'''Tests the save code of the SecretKey class'''
	test_folder = setup_test('encryption_secretkey_save')

	key = EncodedString(r"XSALSA20:J~T^ko3HCFb$1Z7NudpcJA-dzDpF52IF1Oysh+CY")
	sk = encryption.SecretKey(key)

	key_path = os.path.join(test_folder, 'testkey.jk')
	status = sk.save(key_path)
	assert not status.error(), "Failed to create saved encryption pair file"

	fhandle = open(key_path)
	filedata = json.load(fhandle)
	fhandle.close()

	assert filedata['SecretKey'] == key.as_string(), "Saved data does not match input data"


def test_secretkey_load():
	'''Tests the load code of the SecretKey class'''
	test_folder = setup_test('encryption_secretkey_load')

	key = EncodedString(r"XSALSA20:J~T^ko3HCFb$1Z7NudpcJA-dzDpF52IF1Oysh+CY")
	sk = encryption.SecretKey(key)

	key_path = os.path.join(test_folder, 'testkey.jk')
	status = sk.save(key_path)
	assert not status.error(), f"Failed to create saved secret key file: {status.info()}"

	status = encryption.load_secretkey(key_path)
	assert not status.error(), f"Failed to load saved secret key file: {status.info()}"

	testpair = status['key']

	assert testpair.type == sk.type, "Loaded data does not match input data"
	assert testpair.enctype == sk.enctype, "Loaded data does not match input data"
	assert testpair.key == key, "Loaded data does not match input data"

def test_secretkey_encrypt_decrypt():
	'''Tests SecretKey encryption/decryption'''

	testdata = b'1234567890'

	sk = encryption.SecretKey()
	encdata = sk.encrypt(testdata)

	newdata = sk.decrypt(encdata)
	assert testdata == newdata, "Decrypted data didn't match"