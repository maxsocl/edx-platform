// Wrapper for RequireJS. It will make the standard requirejs(), require(), and
// define() functions from Require JS available inside the anonymous function.
//
// See https://edx-wiki.atlassian.net/wiki/display/LMS/Integration+of+Require+JS+into+the+system
(function (requirejs, require, define) {

define(['logme', 'update_input'], function (logme, updateInput) {
    return Draggables;

    function Draggables(state) {
        var c1;

        state.draggables = [];

        for (c1 = 0; c1 < state.config.draggables.length; c1 += 1) {
            processDraggable(state.config.draggables[c1], c1 + 1);
        }

        state.currentMovingDraggable = null;

        $(document).mousemove(function (event) {
            normalizeEvent(event);

            if (state.currentMovingDraggable !== null) {
                state.currentMovingDraggable.iconEl.css(
                    'left',
                    event.pageX -
                        state.baseImageEl.offset().left -
                        state.currentMovingDraggable.iconWidth * 0.5
                );
                state.currentMovingDraggable.iconEl.css(
                    'top',
                    event.pageY -
                        state.baseImageEl.offset().top -
                        state.currentMovingDraggable.iconHeight * 0.5
                );
            }
        });

        return;

        function processDraggable(obj, objIndex) {
            var inContainer, mousePressed, onTarget, draggableObj, marginCss;

            draggableObj = {};

            draggableObj.zIndex = objIndex;

            draggableObj.containerEl = $(
                '<div ' +
                    'style=" ' +
                        'width: 100px; ' +
                        'height: 100px; ' +
                        'display: inline; ' +
                        'float: left; ' +
                        'overflow: hidden; ' +
                        'z-index: ' + objIndex + '; ' +
                        'border: 1px solid #CCC; ' +
                        'text-align: center; ' +
                        'position: relative; ' +
                    '" ' +
                    '></div>'
            );
            draggableObj.containerEl.appendTo(state.sliderEl);

            if (obj.icon.length > 0) {
                draggableObj.iconEl = $('<img />');
                draggableObj.iconEl.attr(
                    'src',
                    state.config.imageDir + '/' + obj.icon
                );
                draggableObj.iconEl.load(function () {
                    draggableObj.iconWidth = this.width;
                    draggableObj.iconHeight = this.height;

                    draggableObj.iconEl.css('position', 'absolute');
                    draggableObj.iconEl.css('top', (50 - this.height * 0.5) + 'px');
                    draggableObj.iconEl.css('left', (50 - this.width * 0.5) + 'px');

                    draggableObj.iconEl.appendTo(draggableObj.containerEl);
                });

                draggableObj.iconEl.mousedown(mouseDown);
                draggableObj.iconEl.mouseup(mouseUp);
                draggableObj.iconEl.mousemove(mouseMove);
            } else {
                // Must fix - add +label support, and just label support.
                return;
            }

            // if (obj.label.length > 0) {
            //     marginCss = '';
            //
            //     if (obj.icon.length === 0) {
            //         marginCss = 'margin-top: 38px;';
            //     }

            //     draggableContainerEl.append(
            //         $('<div style="clear: both; text-align: center; ' + marginCss + ' ">' + obj.label + '</div>')
            //     );
            // }

            inContainer = true;
            mousePressed = false;

            onTarget = null;

            draggableObj.id = obj.id;
            draggableObj.x = -1;
            draggableObj.y = -1;

            draggableObj.setInContainer = function (val) { inContainer = val; };
            draggableObj.setOnTarget = function (val) { onTarget = val; };

            state.draggables.push(draggableObj);

            return;

            function mouseDown(event) {
                if (mousePressed === false) {
                    state.currentMovingDraggable = draggableObj;
                    normalizeEvent(event);

                    if (inContainer === true) {
                        draggableObj.containerEl.hide();

                        draggableObj.iconEl.detach();
                        draggableObj.iconEl.css('left', event.pageX - state.baseImageEl.offset().left - draggableObj.iconWidth * 0.5);
                        draggableObj.iconEl.css('top', event.pageY - state.baseImageEl.offset().top - draggableObj.iconHeight * 0.5);
                        draggableObj.iconEl.appendTo(state.baseImageEl.parent());

                        inContainer = false;
                    }

                    draggableObj.oldZIndex = draggableObj.zIndex;
                    draggableObj.zIndex = 1000;
                    draggableObj.iconEl.css('z-index', '1000');

                    mousePressed = true;
                    event.preventDefault();
                }
            }

            function mouseUp() {
                if (mousePressed === true) {
                    state.currentMovingDraggable = null;

                    checkLandingElement();
                }
            }

            function mouseMove() {
                if (mousePressed === true) {
                    draggableObj.iconEl.css('left', event.pageX - state.baseImageEl.offset().left - draggableObj.iconWidth * 0.5);
                    draggableObj.iconEl.css('top', event.pageY - state.baseImageEl.offset().top - draggableObj.iconHeight * 0.5);
                }
            }

            // At this point the mouse was realeased, and we need to check
            // where the draggable eneded up. Based on several things, we
            // will either move the draggable back to the slider, or update
            // the input with the user's answer (X-Y position of the draggable,
            // or the ID of the target where it landed.
            function checkLandingElement() {
                var offsetIE, targetFound;

                mousePressed = false;

                offsetIE = draggableObj.iconEl.position();

                if (state.individualTargets === true) {
                    targetFound = false;

                    checkIfOnTarget();

                    if (targetFound === true) {
                        correctZIndexes();
                    } else {
                        moveBackToSlider();
                        removeObjIdFromTarget();
                    }
                } else {
                    if (
                        (offsetIE.left < 0) ||
                        (offsetIE.left + draggableObj.iconWidth > state.baseImageEl.width()) ||
                        (offsetIE.top < 0) ||
                        (offsetIE.top + draggableObj.iconHeight > state.baseImageEl.height())
                    ) {
                        moveBackToSlider();

                        draggableObj.x = -1;
                        draggableObj.y = -1;
                    } else {
                        correctZIndexes();

                        draggableObj.x = offsetIE.left + draggableObj.iconWidth * 0.5;
                        draggableObj.y = offsetIE.top + draggableObj.iconHeight * 0.5;
                    }
                }

                state.updateArrowOpacity();
                updateInput(state);

                return;

                function removeObjIdFromTarget() {
                    var c1;

                    if (onTarget !== null) {
                        for (c1 = 0; c1 < onTarget.draggable.length; c1 += 1) {
                            if (onTarget.draggable[c1] === draggableObj.id) {
                                onTarget.draggable.splice(c1, 1);

                                break;
                            }
                        }

                        onTarget = null;
                    }
                }

                // Determine if a draggable, after it was relased, ends up on a
                // target. We do this by iterating over all of the targets, and
                // for each one we check whether the draggable's center is
                // within the target's dimensions.
                function checkIfOnTarget() {
                    var c1, target;

                    for (c1 = 0; c1 < state.targets.length; c1 += 1) {
                        target = state.targets[c1];

                        if (offsetIE.top + draggableObj.iconHeight * 0.5 < target.offset.top) {
                            continue;
                        }
                        if (offsetIE.top + draggableObj.iconHeight * 0.5 > target.offset.top + target.h) {
                            continue;
                        }
                        if (offsetIE.left + draggableObj.iconWidth * 0.5 < target.offset.left) {
                            continue;
                        }
                        if (offsetIE.left + draggableObj.iconWidth * 0.5 > target.offset.left + target.w) {
                            continue;
                        }

                        if (
                            (state.config.one_per_target === true) &&
                            (target.draggable.length === 1) &&
                            (target.draggable[0] !== draggableObj.id)
                        ) {
                            continue;
                        }

                        targetFound = true;

                        // If the draggable was moved from one target to
                        // another, then we need to remove it's ID from the
                        // previous target's draggables list, and add it to the
                        // new target's draggables list.
                        if ((onTarget !== null) && (onTarget.id !== target.id)) {
                            removeObjIdFromTarget();
                            onTarget = target;
                            target.draggable.push(draggableObj.id);
                        } else if (onTarget === null) {
                            onTarget = target;
                            target.draggable.push(draggableObj.id);
                        }

                        // Reposition the draggable so that it's center
                        // coincides with the center of the target.
                        snapToTarget(target);

                        break;
                    }
                }

                function snapToTarget(target) {
                    var offset;

                    offset = 0;
                    if (state.config.targetOutline === true) {
                        offset = 1;
                    }

                    draggableObj.iconEl.css('left', target.offset.left + 0.5 * target.w - draggableObj.iconWidth * 0.5 + offset);
                    draggableObj.iconEl.css('top', target.offset.top + 0.5 * target.h - draggableObj.iconHeight * 0.5 + offset);
                }

                // Go through all of the draggables subtract 1 from the z-index
                // of all whose z-index is higher than the old z-index of the
                // current element. After, set the z-index of the current
                // element to 1 + N (where N is the number of draggables - i.e.
                // the highest z-index possible).
                //
                // This will make sure that after releasing a draggable, it
                // will be on top of all of the other draggables. Also, the
                // ordering of the visibility (z-index) of the other draggables
                // will not change.
                function correctZIndexes() {
                    var c1;

                    for (c1 = 0; c1 < state.draggables.length; c1++) {
                        if (draggableObj.oldZIndex < state.draggables[c1].zIndex) {
                            state.draggables[c1].zIndex -= 1;
                            state.draggables[c1].iconEl.css(
                                'z-index',
                                state.draggables[c1].zIndex
                            );
                        }
                    }

                    draggableObj.zIndex = c1;
                    draggableObj.iconEl.css('z-index', c1);
                }

                // If a draggable was released in a wrong positione, we will
                // move it back to the slider, placing it in the same position
                // that it was dragged out of.
                function moveBackToSlider() {
                    var c1;

                    draggableObj.containerEl.show();

                    draggableObj.iconEl.detach();

                    draggableObj.iconEl.css('top', (50 - draggableObj.iconHeight * 0.5) + 'px');
                    draggableObj.iconEl.css('left', (50 - draggableObj.iconWidth * 0.5) + 'px');

                    draggableObj.iconEl.appendTo(draggableObj.containerEl);

                    inContainer = true;
                }
            }
        }

        // In firefox the event does not have a proper pageX and pageY
        // coordinates.
        function normalizeEvent(event) {
            if(!event.offsetX) {
                event.offsetX = (event.pageX - $(event.target).offset().left);
                event.offsetY = (event.pageY - $(event.target).offset().top);
            }
            return event;
        }
    }
});

// End of wrapper for RequireJS. As you can see, we are passing
// namespaced Require JS variables to an anonymous function. Within
// it, you can use the standard requirejs(), require(), and define()
// functions as if they were in the global namespace.
}(RequireJS.requirejs, RequireJS.require, RequireJS.define)); // End-of: (function (requirejs, require, define)
