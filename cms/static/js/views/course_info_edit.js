/*  this view should own everything on the page which has controls effecting its operation
   generate other views for the individual editors.
   The render here adds views for each update/handout by delegating to their collections but does not
   generate any html for the surrounding page.
*/
CMS.Views.CourseInfoEdit = Backbone.View.extend({
  // takes CMS.Models.CourseInfo as model
  tagName: 'div',

  render: function() {
    // instantiate the ClassInfoUpdateView and delegate the proper dom to it
    new CMS.Views.ClassInfoUpdateView({
        el: $('body.updates'),
        collection: this.model.get('updates')
    });

    new CMS.Views.ClassInfoHandoutsView({
        el: this.$('#course-handouts-view'),
        model: this.model.get('handouts')
    });
    return this;
  }
});

// ??? Programming style question: should each of these classes be in separate files?
CMS.Views.ClassInfoUpdateView = Backbone.View.extend({
    // collection is CourseUpdateCollection
    events: {
        "click .new-update-button" : "onNew",
        "click #course-update-view .save-button" : "onSave",
        "click #course-update-view .cancel-button" : "onCancel",
        "click .post-actions > .edit-button" : "onEdit",
        "click .post-actions > .delete-button" : "onDelete"
    },
        
    initialize: function() {
    	var self = this;
        // instantiates an editor template for each update in the collection
        window.templateLoader.loadRemoteTemplate("course_info_update",
        	// TODO Where should the template reside? how to use the static.url to create the path?
            "/static/client_templates/course_info_update.html",
            function (raw_template) {
        		self.template = _.template(raw_template);
        		self.render();           
            }
        );
    },
        
    render: function () {
          // iterate over updates and create views for each using the template
          var updateEle = this.$el.find("#course-update-list");
          // remove and then add all children
          $(updateEle).empty();
          var self = this;
          this.collection.each(function (update) {
        	  var newEle = self.template({ updateModel : update });
              $(updateEle).append(newEle);
          });
          this.$el.find(".new-update-form").hide();
          this.$el.find('.date').datepicker({ 'dateFormat': 'MM d, yy' });
          return this;
    },
    
    onNew: function(event) {
        event.preventDefault();
        var self = this;
        // create new obj, insert into collection, and render this one ele overriding the hidden attr
        var newModel = new CMS.Models.CourseUpdate();
        this.collection.add(newModel, {at : 0});
        
        var $newForm = $(this.template({ updateModel : newModel }));

        var updateEle = this.$el.find("#course-update-list");
        $(updateEle).prepend($newForm);

        var $textArea = $newForm.find(".new-update-content").first();
        if (this.$codeMirror == null ) {
            this.$codeMirror = CodeMirror.fromTextArea($textArea.get(0), {
                mode: "text/html",
                lineNumbers: true,
                lineWrapping: true,
            });
        }
        
        $newForm.addClass('editing');
        this.$currentPost = $newForm.closest('li');

        window.$modalCover.show();
        window.$modalCover.bind('click', function() {
            self.closeEditor(self, true);
        });

        $('.date').datepicker('destroy');
        $('.date').datepicker({ 'dateFormat': 'MM d, yy' });
    },
    
    onSave: function(event) {
        event.preventDefault();
        var targetModel = this.eventModel(event);
        targetModel.set({ date : this.dateEntry(event).val(), content : this.$codeMirror.getValue() });
        // push change to display, hide the editor, submit the change        
        targetModel.save({}, {error : CMS.ServerError});
        this.closeEditor(this);
    },
    
    onCancel: function(event) {
        event.preventDefault();
        // change editor contents back to model values and hide the editor
        $(this.editor(event)).hide();
        var targetModel = this.eventModel(event);
        this.closeEditor(this, !targetModel.id);
    },
    
    onEdit: function(event) {
        event.preventDefault();
        var self = this;
        this.$currentPost = $(event.target).closest('li');
        this.$currentPost.addClass('editing');
       
        $(this.editor(event)).show();
        var $textArea = this.$currentPost.find(".new-update-content").first();
        if (this.$codeMirror == null ) {
            this.$codeMirror = CodeMirror.fromTextArea($textArea.get(0), {
                mode: "text/html",
                lineNumbers: true,
                lineWrapping: true,
            });
        }

        window.$modalCover.show();
        var targetModel = this.eventModel(event);
        window.$modalCover.bind('click', function() {
            self.closeEditor(self);
        });
    },

    onDelete: function(event) {
        event.preventDefault();
        // TODO ask for confirmation
        // remove the dom element and delete the model
        var targetModel = this.eventModel(event);
        this.modelDom(event).remove();
        var cacheThis = this;
        targetModel.destroy({success : function (model, response) { 
            cacheThis.collection.fetch({success : function() {cacheThis.render();},
                error : CMS.ServerError});
        },
        error : CMS.ServerError
        });
    },

    closeEditor: function(self, removePost) {
        var targetModel = self.collection.getByCid(self.$currentPost.attr('name'));

        if(removePost) {
            self.$currentPost.remove();
        }

        // close the modal and insert the appropriate data
        self.$currentPost.removeClass('editing');
        self.$currentPost.find('.date-display').html(targetModel.get('date'));
        self.$currentPost.find('.date').val(targetModel.get('date'));
        self.$currentPost.find('.update-contents').html(targetModel.get('content'));
        self.$currentPost.find('.new-update-content').val(targetModel.get('content'));
        self.$currentPost.find('form').hide();
        window.$modalCover.unbind('click');
        window.$modalCover.hide();
        this.$codeMirror = null;
        self.$currentPost.find('.CodeMirror').remove();
    },
    
    // Dereferencing from events to screen elements    
    eventModel: function(event) {
        // not sure if it should be currentTarget or delegateTarget
        return this.collection.getByCid($(event.currentTarget).attr("name"));
    },
        
    modelDom: function(event) {
        return $(event.currentTarget).closest("li");
    },
            
    editor: function(event) {
    	var li = $(event.currentTarget).closest("li");
    	if (li) return $(li).find("form").first();
    },

    dateEntry: function(event) {
    	var li = $(event.currentTarget).closest("li");
    	if (li) return $(li).find(".date").first();
    },

    contentEntry: function(event) {
        return $(event.currentTarget).closest("li").find(".new-update-content").first();
    },
        
    dateDisplay: function(event) {
        return $(event.currentTarget).closest("li").find("#date-display").first();
    },

    contentDisplay: function(event) {
        return $(event.currentTarget).closest("li").find(".update-contents").first();
    }
        
});

// the handouts view is dumb right now; it needs tied to a model and all that jazz
CMS.Views.ClassInfoHandoutsView = Backbone.View.extend({
    // collection is CourseUpdateCollection
    events: {
        "click .save-button" : "onSave",
        "click .cancel-button" : "onCancel",
        "click .edit-button" : "onEdit"
    },

    initialize: function() {
        var self = this;
        this.model.fetch(
            {
                complete: function() {
                    window.templateLoader.loadRemoteTemplate("course_info_handouts",
                        "/static/client_templates/course_info_handouts.html",
                        function (raw_template) {
                            self.template = _.template(raw_template);
                            self.render();                
                        }
                    );
                },
                error : CMS.ServerError
            }
        );
    },
        
    render: function () {        
        var updateEle = this.$el;
        var self = this;
        this.$el.html(
            $(this.template( {
                model: this.model
                })
            )
        );
        this.$preview = this.$el.find('.handouts-content');
        this.$form = this.$el.find(".edit-handouts-form");
        this.$editor = this.$form.find('.handouts-content-editor');
        this.$form.hide();

        return this;
    },

    onEdit: function(event) {
        var self = this;
        this.$editor.val(this.$preview.html());
        this.$form.show();
        if (this.$codeMirror == null) {
            this.$codeMirror = CodeMirror.fromTextArea(this.$editor.get(0), {
                mode: "text/html",
                lineNumbers: true,
                lineWrapping: true,
            });
        }
        window.$modalCover.show();
        window.$modalCover.bind('click', function() {
            self.closeEditor(self);
        });
    },

    onSave: function(event) {
        this.model.set('data', this.$codeMirror.getValue());
        this.render();
        this.model.save({}, {error: CMS.ServerError});
        this.$form.hide();
        this.closeEditor(this);
    },

    onCancel: function(event) {
        this.$form.hide();
        this.closeEditor(this);
    },

    closeEditor: function(self) {
        this.$form.hide();
        window.$modalCover.unbind('click');
        window.$modalCover.hide();
        self.$form.find('.CodeMirror').remove();
        this.$codeMirror = null;
    }
});