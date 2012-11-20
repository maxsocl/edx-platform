CMS.Models.Location = Backbone.Models.extend({
	defaults: {
		tag: "",
		org: "",
		course: "",
		category: "",
		name: ""
	},
	toUrl: function(overrides) {
		return
			(overrides['tag'] ? overrides['tag'] : this.get('tag')) + "://" +
			(overrides['org'] ? overrides['org'] : this.get('org')) + "/" +
			(overrides['course'] ? overrides['course'] : this.get('course')) + "/" +
			(overrides['category'] ? overrides['category'] : this.get('category')) + "/" +
			(overrides['name'] ? overrides['name'] : this.get('name')) + "/";
	},
	_tagPattern = /[^:]+/g,
	_fieldPattern = new RegExp('[^/]+','g'),
	
	parse: function(payload) {
		if (payload instanceof Array) {
			return {
				tag: payload[0],
				name: payload[1],
				course: payload[2],
				category: payload[3],
				name: payload[4]
			}
		}
		else if (payload instanceof String) {
			var foundTag = this._tagPattern.exec(payload);
			if (foundTag) {
				this._fieldPattern.lastIndex = this._tagPattern.lastIndex;
				return {
					tag: foundTag,
					name: this._fieldPattern.exec(payload),
					course: this._fieldPattern.exec(payload),
					category: this._fieldPattern.exec(payload),
					name: this._fieldPattern.exec(payload)
				}
			}
			else return null;
		}
		else {
			return payload;
		}
	}
});

CMS.Models.CourseRelative = Backbone.Models.extend({
	defaults: {
		course_location : null, // must never be null, but here to doc the field
		idx : null	// the index making it unique in the containing collection (no implied sort)
	}
});

CMS.Models.CourseRelativeCollection = Backbone.Collections.extend({
	model : CourseRelative
});