'''The userprofile module handles user profile management'''
import json
import os
import platform
import shutil
import sqlite3
import uuid

from retval import RetVal, ResourceExists, ExceptionThrown, BadParameterValue, ResourceNotFound
import utils

BadProfileList = 'BadProfileList'
InvalidProfile = 'InvalidProfile'

class Profile:
	'''Encapsulates data for user profiles'''
	def __init__(self, name=''):
		self.name = name
		self.isdefault = False
		self.id = ''
		self.wid = ''
		self.domain = ''
		self.port = 2001
	
	def __str__(self):
		return str(self.as_dict())

	def make_id(self):
		'''Generates a new profile ID for the object'''
		self.id = str(uuid.uuid4())

	def address(self):
		'''Returns the identity workspace address for the profile'''
		return '/'.join([self.wid, self.domain])
	
	def serverstring(self):
		'''Returns the identity workspace address for the profile including port'''
		return ':'.join([self.address(),self.port])
	
	def as_dict(self):
		'''Returns the state of the profile as JSON'''
		return {
			'name' : self.name,
			'isdefault' : self.isdefault,
			'id' : self.id,
			'wid' : self.wid,
			'domain' : self.domain,
			'port' : self.port
		}
	
	def set_from_dict(self, data):
		'''Assigns profile data from a JSON string'''
		
		for k,v in data.items():
			if k in [ 'name', 'isdefault', 'id', 'wid', 'domain', 'port' ]:
				setattr(self, k, v)
	
	def is_valid(self):
		'''Returns true if data stored in the profile object is valid'''
		if self.name and utils.validate_uuid(self.id):
			return True
		
		return False


class ProfileManager:
	'''Handles user profile management'''
	
	def __init__(self, profile_path=''):
		if profile_path:
			self.profile_folder = profile_path
		else:
			osname = platform.system().casefold()
			if osname == 'windows':
				self.profile_folder = os.path.join(os.getenv('LOCALAPPDATA'), 'anselus')
			else:
				self.profile_folder = os.path.join(os.getenv('HOME'), '.config','anselus')
		
		if not os.path.exists(self.profile_folder):
			os.mkdir(self.profile_folder)
		
		self.profiles = list()
		self.default_profile = ''
		self.active_index = -1
		self.profile_id = ''
		
		self.db = None
		self.dbfolder = ''
		self.dbpath = ''

		# Activate the default profile. If one doesn't exist, create one
		self.error_state = self.load_profiles()
		
		if not self.get_profiles():
			self.error_state = self.create_profile('primary')
			if not self.error_state.error():
				self.set_default_profile('primary')
		
		if not self.error_state.error():
			self.error_state = self.activate_profile(self.get_default_profile())

	def save_profiles(self):
		'''
		Saves the current list of profiles to the profile list file.

		Returns:
		"error" : error state - string
		'''
		if self.error_state.error():
			return self.error_state
		
		profile_list_path = os.path.join(self.profile_folder, 'profiles.json')
		
		if not os.path.exists(self.profile_folder):
			os.mkdir(self.profile_folder)

		try:
			with open(profile_list_path, 'w') as fhandle:
				profile_data = list()
				for profile in self.profiles:

					if not profile.is_valid():
						return RetVal(InvalidProfile, profile.name)
					
					profile_data.append(profile.as_dict())

					item_folder = os.path.join(self.profile_folder, profile.name)
					if not os.path.exists(item_folder):
						os.mkdir(item_folder)

				json.dump(profile_data, fhandle, ensure_ascii=False, indent=1)
			
		except Exception as e:
			return RetVal(ExceptionThrown, e.__str__())

		return RetVal()

	def load_profiles(self):
		'''
		Loads profile information from the specified JSON file stored in the top level of the 
		profile folder.

		Returns:
		"error" : string
		"profiles" : list
		'''
		profile_list_path = os.path.join(self.profile_folder, 'profiles.json')
		
		if os.path.exists(profile_list_path):
			profile_data = list()
			try:
				with open(profile_list_path, 'r') as fhandle:
					profile_data = json.load(fhandle)
				
			except Exception:
				return RetVal(BadProfileList)

			profiles = list()
			for item in profile_data:
				profile = Profile()
				profile.set_from_dict(item)
				profiles.append(profile)
				if profile.isdefault:
					self.default_profile = profile.name

			self.profiles = profiles
		return RetVal()
	
	def get_db(self):
		'''Returns a handle to the profile manager's database connection'''
		return self.db

	def __index_for_profile(self, name):
		'''Returns the numeric index of the named profile. Returns -1 on error'''
		if not name:
			return -1
		
		name_squashed = name.casefold()
		for i in range(0, len(self.profiles)):
			if name_squashed == self.profiles[i].name:
				return i
		return -1

	def create_profile(self, name):
		'''
		Creates a profile with the specified name. Profile names are not case-sensitive.

		Returns:
		"error" : string
		"id" : uuid of folder for new profile
		'''
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		if self.__index_for_profile(name_squashed) >= 0:
			return RetVal(ResourceExists, name)

		profile = Profile(name)
		profile.make_id()
		self.profiles.append(profile)

		if len(self.profiles) == 1:
			profile.isdefault = True
			self.default_profile = name
		
		return self.save_profiles()

	def delete_profile(self, name):
		'''
		Deletes the named profile and all files on disk contained in it.

		Returns:
		"error" : string
		'''
		if name == 'default':
			return RetVal(BadParameterValue, "'default' is reserved")
		
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		itemindex = self.__index_for_profile(name_squashed)
		if itemindex < 0:
			return RetVal(ResourceNotFound, "%s doesn't exist" % name)

		profile = self.profiles.pop(itemindex)
		profile_path = os.path.join(self.profile_folder, profile.id)
		if os.path.exists(profile_path):
			try:
				shutil.rmtree(profile_path)
			except Exception as e:
				return RetVal(ExceptionThrown, e.__str__())
		
		if profile.isdefault:
			if self.profiles:
				self.profiles[0].isdefault = True
		
		return self.save_profiles()

	def rename_profile(self, oldname, newname):
		'''
		Renames a profile, leaving the profile ID unchanged.

		Returns:
		"error" : string
		'''
		
		if not oldname or not newname:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		old_squashed = oldname.casefold()
		new_squashed = newname.casefold()

		if old_squashed == new_squashed:
			return RetVal()
		
		index = self.__index_for_profile(old_squashed)
		if index < 0:
			return RetVal(ResourceNotFound, "%s doesn't exist" % oldname)

		if self.__index_for_profile(new_squashed):
			return RetVal(ResourceExists, "%s already exists" % newname)

		self.profiles[index].name = new_squashed
		return self.save_profiles()
	
	def get_profiles(self):
		'''Returns a list of loaded profiles'''
		return self.profiles
	
	def get_default_profile(self):
		'''
		Returns the name of the default profile. If one has not been set, it returns an empty string.
		'''
		for item in self.profiles:
			if item.isdefault:
				return item.name
		return ''

	def set_default_profile(self, name):
		'''
		Sets the default profile. If there is only one profile -- or none at all -- this call has 
		no effect.
		'''
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		if len(self.profiles) == 1:
			if self.profiles[0].isdefault:
				return RetVal()
			self.profiles[0].isdefault = True
			return self.save_profiles()
		
		oldindex = -1
		for i in range(0, len(self.profiles)):
			if self.profiles[i].isdefault:
				oldindex = i
		
		name_squashed = name.casefold()
		newindex = self.__index_for_profile(name_squashed)
		
		if newindex < 0:
			return RetVal(ResourceNotFound, "New profile %s not found" % name_squashed)
		
		if oldindex >= 0:
			if name_squashed == self.profiles[oldindex].name:
				return RetVal()
			self.profiles[oldindex].isdefault = False

		self.profiles[newindex].isdefault = True		
		return self.save_profiles()

	def activate_profile(self, name):
		'''
		Activates the specified profile.

		Returns:
		"error" : string
		"wid" : string
		"host" : string
		"port" : integer
		'''
		if self.active_index >= 0:
			self.db.close()
			self.active_index = -1
		
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		active_index = self.__index_for_profile(name_squashed)
		if active_index < 0:
			return RetVal(ResourceNotFound, "%s doesn't exist" % name_squashed)
		
		self.dbfolder = os.path.join(self.profile_folder, name_squashed)
		self.dbpath = os.path.join(self.dbfolder, 'storage.db')
		if os.path.exists(self.dbpath):
			self.db = sqlite3.connect(self.dbpath)
		else:
			self.reset_db()
		self.profile_id = name_squashed

		self.active_index = active_index
		
		out = RetVal()
		out.set_values({
			'wid' : self.profiles[active_index].wid,
			'host' : self.profiles[active_index].domain,
			'port' : self.profiles[active_index].port 
		})
		return out

	def get_active_profile(self):
		'''Returns the active profile name'''
		if self.active_index >= 0:
			return self.profiles[self.active_index]
		return ''

	def reset_db(self):
		'''This function reinitializes the database to empty, taking a path to the file used by the 
		SQLite database. Returns a handle to an open SQLite3 connection.
		'''
		if os.path.exists(self.dbpath):
			try:
				os.remove(self.dbpath)
			except Exception as e:
				print('Unable to delete old database %s: %s' % (self.dbpath, e))
		
		db = sqlite3.connect(self.dbpath)
		cursor = db.cursor()

		sqlcmds = [ '''
			CREATE TABLE workspaces (
				"wid" TEXT NOT NULL UNIQUE,
				"friendly_address" TEXT,
				"domain" TEXT,
				"password" TEXT,
				"pwhashtype" TEXT,
				"type" TEXT
			);''', '''
			CREATE table "folders"(
				"fid" TEXT NOT NULL UNIQUE,
				"address" TEXT NOT NULL,
				"keyid" TEXT NOT NULL,
				"path" TEXT NOT NULL,
				"permissions" TEXT NOT NULL
			);''', '''
			CREATE table "sessions"(
				"address" TEXT NOT NULL,
				"devid" TEXT NOT NULL,
				"devname" TEXT,
				"session_str" TEXT NOT NULL
			);''', '''
			CREATE table "keys"(
				"keyid" TEXT NOT NULL UNIQUE,
				"address" TEXT NOT NULL,
				"type" TEXT NOT NULL,
				"category" TEXT NOT NULL,
				"private" TEXT NOT NULL,
				"public" TEXT,
				"algorithm" TEXT NOT NULL
			);''', '''
			CREATE table "messages"(
				"id" TEXT NOT NULL UNIQUE,
				"from"  TEXT NOT NULL,
				"address" TEXT NOT NULL,
				"cc"  TEXT,
				"bcc" TEXT,
				"date" TEXT NOT NULL,
				"thread_id" TEXT NOT NULL,
				"subject" TEXT,
				"body" TEXT,
				"attachments" TEXT
			);''', '''
			CREATE TABLE "contacts" (
				"id"	TEXT NOT NULL,
				"sensitivity"	TEXT NOT NULL,
				"source"	TEXT NOT NULL,
				"fieldname"	TEXT,
				"fieldvalue"	TEXT
			);''', '''
			CREATE TABLE "notes" (
				"id"	TEXT NOT NULL UNIQUE,
				"address" TEXT,
				"title"	TEXT,
				"body"	TEXT,
				"notebook"	TEXT,
				"tags"	TEXT,
				"created"	TEXT NOT NULL,
				"updated"	TEXT,
				"attachments"	TEXT
			);''', '''
			CREATE TABLE "files" (
				"id"	TEXT NOT NULL UNIQUE,
				"name"	TEXT NOT NULL,
				"type"	TEXT NOT NULL,
				"path"	TEXT NOT NULL
			);'''
		]

		for sqlcmd in sqlcmds:
			cursor = db.cursor()
			cursor.execute(sqlcmd)
		db.commit()
		return db

