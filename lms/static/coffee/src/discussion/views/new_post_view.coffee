class @NewPostView extends Backbone.View

    initialize: () ->
        @dropdownButton = @$(".topic_dropdown_button")
        @topicMenu      = @$(".topic_menu_wrapper")

        @menuOpen = @dropdownButton.hasClass('dropped')

        @topicId    = @$(".topic").first().data("discussion_id")
        @topicText  = @getFullTopicName(@$(".topic").first())

        @maxNameWidth = 100
        @setSelectedTopic()

    events:
        "submit .new-post-form":            "createPost"
        "click  .topic_dropdown_button":    "toggleTopicDropdown"
        "click  .topic_menu_wrapper":       "setTopic"
        "click  .topic_menu_search":        "ignoreClick"

    # Because we want the behavior that when the body is clicked the menu is
    # closed, we need to ignore clicks in the search field and stop propagation.
    # Without this, clicking the search field would also close the menu.
    ignoreClick: (event) ->
        event.stopPropagation()

    toggleTopicDropdown: (event) ->
        event.stopPropagation()
        if @menuOpen
            @hideTopicDropdown()
        else
            @showTopicDropdown()
    
    showTopicDropdown: () ->
        @menuOpen = true
        @dropdownButton.addClass('dropped')
        @topicMenu.show()

        $('body').bind 'click', @hideTopicDropdown

        # Set here because 1) the window might get resized and things could
        # change and 2) can't set in initialize because the button is hidden
        @maxNameWidth = @dropdownButton.width() * 0.9

    # Need a fat arrow because hideTopicDropdown is passed as a callback to bind
    hideTopicDropdown: () =>
        @menuOpen = false
        @dropdownButton.removeClass('dropped')
        @topicMenu.hide()

        $('body').unbind 'click', @hideTopicDropdown

    setTopic: (event) ->
        $target = $(event.target)
        if $target.data('discussion_id')
            @topicText = $target.html()
            @topicText  = @getFullTopicName($target)
            @topicId   = $target.data('discussion_id')
            @setSelectedTopic()

    setSelectedTopic: ->
        @dropdownButton.html(@fitName(@topicText) + ' <span class="drop-arrow">▾</span>')

    getFullTopicName: (topicElement) ->
        name = topicElement.html()
        topicElement.parents('ul').not('.topic_menu').each ->
            name = $(this).siblings('a').html() + ' / ' + name
        return name

    getNameWidth: (name) ->
        test = $("<div>")
        test.css 
            "font-size": @dropdownButton.css('font-size')
            opacity: 0
            position: 'absolute'
            left: -1000
            top: -1000
        $("body").append(test)
        test.html(name)
        width = test.width()
        test.remove()
        return width
    
    fitName: (name) ->
        width = @getNameWidth(name)
        if width < @maxNameWidth
            return name
        path = (x.replace /^\s+|\s+$/g, "" for x in name.split("/"))
        while path.length > 1
            path.shift()
            partialName = "... / " + path.join(" / ")
            if  @getNameWidth(partialName) < @maxNameWidth
                return partialName

        rawName = path[0]

        name = "... / " + rawName

        while @getNameWidth(name) > @maxNameWidth
            rawName = rawName[0...rawName.length-1]
            name =  "... / " + rawName + " ..."

        return name


    createPost: (event) ->
        event.preventDefault()
        title   = @$(".new-post-title").val()
        body    = @$(".new-post-body").val()
        tags    = @$(".new-post-tags").val()

        anonymous = false || @$("input.discussion-anonymous").is(":checked")
        follow    = false || @$("input.discussion-follow").is(":checked")

        $formTopicDropBtn.bind('click', showFormTopicDrop);
        $formTopicDropMenu.bind('click', setFormTopic);

        url = DiscussionUtil.urlFor('create_thread', @topicId)

        DiscussionUtil.safeAjax
            $elem: $(event.target)
            $loading: $(event.target) if event
            url: url
            type: "POST"
            dataType: 'json'
            async: false # TODO when the rest of the stuff below is made to work properly..
            data:
                title: title
                body: body
                tags: tags
                anonymous: anonymous
                auto_subscribe: follow
            error: DiscussionUtil.formErrorHandler(@$(".new-post-form-errors"))
            success: (response, textStatus) =>
                thread = new Thread response['content']
                DiscussionUtil.clearFormErrors(@$(".new-post-form-errors"))
                @$el.hide()
                @$(".new-post-title").val("").attr("prev-text", "")
                @$(".new-post-body").val("").attr("prev-text", "")
                @$(".new-post-tags").val("")
                @$(".new-post-tags").importTags("")
                @collection.add thread
                @collection.trigger "reset"
                @trigger "thread:created", thread.id

                #@$el.children(".threads").prepend($thread)
                # no idea what this is
                #@$el.children(".blank").remove()
                #@$(".new-post-similar-posts").empty()
                #@$(".new-post-similar-posts-wrapper").hide()
                #DiscussionUtil.setWmdContent @$el, $.proxy(@$, @), "new-post-body", ""

                #thread = @model.addThread response.content
                #threadView = new ThreadView el: $thread[0], model: thread
                #thread.updateInfo response.annotated_content_info
                #@cancelNewPost()
