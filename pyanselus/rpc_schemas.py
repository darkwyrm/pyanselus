greeting = {
	'title' : 'Anselus Hello Message',
	'type' : 'object',
	'required' : [ 'Name', 'Version', 'Code', 'Status' ],
	'properties' : {
		'Name' : {
			'type' : 'string'
		},
		'Version' : {
			'type' : 'string'
		},
		'Code' : {
			'type' : 'integer'
		},
		'Status' : {
			'type' : 'string'
		}
	}
}

server_response = {
	'title' : 'Anselus Server Response',
	'type' : 'object',
	'required' : [ 'Code', 'Status', 'Data' ],
	'properties' : {
		'Code' : {
			'type' : 'integer'
		},
		'Status' : {
			'type' : 'string'
		},
		'Data' : {
			'type' : 'object'
		}
	}
}
