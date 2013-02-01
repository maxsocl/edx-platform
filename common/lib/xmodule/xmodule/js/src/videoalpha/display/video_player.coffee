class @VideoPlayerAlpha extends SubviewAlpha
  initialize: ->
    if @video.videoType is 'youtube'
      @PlayerState = YT.PlayerState
      # Define a missing constant of Youtube API
      @PlayerState.UNSTARTED = -1
    else if @video.videoType is 'html5'
      @PlayerState = HTML5Video.PlayerState

    @currentTime = 0
    @el = $("#video_#{@video.id}")

  bind: ->
    console.log "show_captions = #{@video.show_captions}"
    $(@control).bind('play', @play)
      .bind('pause', @pause)
    $(@qualityControl).bind('changeQuality', @handlePlaybackQualityChange)
    if @video.show_captions is true
      $(@caption).bind('seek', @onSeek)
    $(@speedControl).bind('speedChange', @onSpeedChange)
    $(@progressSlider).bind('seek', @onSeek)
    if @volumeControl
      $(@volumeControl).bind('volumeChange', @onVolumeChange)
    $(document).keyup @bindExitFullScreen

    @$('.add-fullscreen').click @toggleFullScreen
    @addToolTip() unless onTouchBasedDevice()

  bindExitFullScreen: (event) =>
    if @el.hasClass('fullscreen') && event.keyCode == 27
      @toggleFullScreen(event)

  render: ->
    @control = new VideoControlAlpha el: @$('.video-controls')
    @qualityControl = new VideoQualityControlAlpha el: @$('.secondary-controls')
    if @video.show_captions is true
      @caption = new VideoCaptionAlpha
        el: @el
        youtubeId: @video.youtubeId('1.0')
        currentSpeed: @currentSpeed()
        captionAssetPath: @video.caption_asset_path
    unless onTouchBasedDevice()
      @volumeControl = new VideoVolumeControlAlpha el: @$('.secondary-controls')
    @speedControl = new VideoSpeedControlAlpha el: @$('.secondary-controls'), speeds: @video.speeds, currentSpeed: @currentSpeed()
    @progressSlider = new VideoProgressSliderAlpha el: @$('.slider')
    @playerVars =
      controls: 0
      wmode: 'transparent'
      rel: 0
      showinfo: 0
      enablejsapi: 1
      modestbranding: 1
    if @video.start
      @playerVars.start = @video.start
      @playerVars.wmode = 'window'
    if @video.end
      # work in AS3, not HMLT5. but iframe use AS3
      @playerVars.end = @video.end
    if @video.videoType is 'html5'
      @player = new HTML5Video.Player @video.el,
        playerVars: @playerVars,
        videoSources: @video.html5Sources,
        events:
          onReady: @onReady
          onStateChange: @onStateChange
          onPlaybackQualityChange: @onPlaybackQualityChange
    else if @video.videoType is 'youtube'
      @player = new YT.Player @video.id,
        playerVars: @playerVars
        videoId: @video.youtubeId()
        events:
          onReady: @onReady
          onStateChange: @onStateChange
          onPlaybackQualityChange: @onPlaybackQualityChange
    if @video.show_captions is true
      @caption.hideCaptions(@['video'].hide_captions)

  addToolTip: ->
    @$('.add-fullscreen, .hide-subtitles').qtip
      position:
        my: 'top right'
        at: 'top center'

  onReady: (event) =>
    unless onTouchBasedDevice()
      $('.video-load-complete:first').data('video').player.play()

  onStateChange: (event) =>
    switch event.data
      when @PlayerState.UNSTARTED
        @onUnstarted()
      when @PlayerState.PLAYING
        @onPlay()
      when @PlayerState.PAUSED
        @onPause()
      when @PlayerState.ENDED
        @onEnded()

  onPlaybackQualityChange: (event, value) =>
    quality = @player.getPlaybackQuality()
    @qualityControl.onQualityChange(quality)

  handlePlaybackQualityChange: (event, value) =>
    @player.setPlaybackQuality(value)

  onUnstarted: =>
    @control.pause()
    if @video.show_captions is true
      @caption.pause()

  onPlay: =>
    @video.log 'play_video'
    window.player.pauseVideo() if window.player && window.player != @player
    window.player = @player
    unless @player.interval
      @player.interval = setInterval(@update, 200)
    if @video.show_captions is true
      @caption.play()
    @control.play()
    @progressSlider.play()

  onPause: =>
    @video.log 'pause_video'
    window.player = null if window.player == @player
    clearInterval(@player.interval)
    @player.interval = null
    if @video.show_captions is true
      @caption.pause()
    @control.pause()

  onEnded: =>
    @control.pause()
    if @video.show_captions is true
      @caption.pause()

  onSeek: (event, time) =>
    @player.seekTo(time, true)
    if @isPlaying()
      clearInterval(@player.interval)
      @player.interval = setInterval(@update, 200)
    else
      @currentTime = time
    @updatePlayTime time

  onSpeedChange: (event, newSpeed) =>
    if @video.videoType is 'youtube'
      @currentTime = Time.convert(@currentTime, parseFloat(@currentSpeed()), newSpeed)
    newSpeed = parseFloat(newSpeed).toFixed(2).replace /\.00$/, '.0'
    @video.setSpeed(newSpeed)
    if @video.videoType is 'youtube'
      if @video.show_captions is true
        @caption.currentSpeed = newSpeed
    if @video.videoType is 'html5'
      @player.setSpeed(newSpeed)
    else if @video.videoType is 'youtube'
      if @isPlaying()
        @player.loadVideoById(@video.youtubeId(), @currentTime)
      else
        @player.cueVideoById(@video.youtubeId(), @currentTime)
    if @video.videoType is 'youtube'
      @updatePlayTime @currentTime

  onVolumeChange: (event, volume) =>
    @player.setVolume volume

  update: =>
    if @currentTime = @player.getCurrentTime()
      @updatePlayTime @currentTime

  updatePlayTime: (time) ->
    progress = Time.format(time) + ' / ' + Time.format(@duration())
    @$(".vidtime").html(progress)
    if @video.show_captions is true
      @caption.updatePlayTime(time)
    @progressSlider.updatePlayTime(time, @duration())

  toggleFullScreen: (event) =>
    event.preventDefault()
    if @el.hasClass('fullscreen')
      @$('.add-fullscreen').attr('title', 'Fill browser')
      @el.removeClass('fullscreen')
    else
      @el.addClass('fullscreen')
      @$('.add-fullscreen').attr('title', 'Exit fill browser')
    if @video.show_captions is true
      @caption.resize()

  # Delegates
  play: =>
    @player.playVideo() if @player.playVideo

  isPlaying: ->
    @player.getPlayerState() == @PlayerState.PLAYING

  pause: =>
    @player.pauseVideo() if @player.pauseVideo

  duration: ->
    if @video.videoType is "youtube"
      return @video.getDuration()
    else if @video.videoType is "html5"
      return @player.getDuration()
    0

  currentSpeed: ->
    @video.speed

  volume: (value) ->
    if value?
      @player.setVolume value
    else
      @player.getVolume()
