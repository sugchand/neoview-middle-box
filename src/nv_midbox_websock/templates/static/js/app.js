'use strict'
angular.module('landingApp', [])
.controller('landingController', ['$scope', '$window', function($scope, $window) {
  var host = "wss://" + $window.location.hostname + ":8080/userwebsocket",
  cameraStatus = [],reload_video=false,
  ws = new WebSocket(host);
  if($window.localStorage.getItem("camera")) {
    $scope.allCamera = true;
  } else {
    $scope.allCamera = false;
  }

  $scope.btnAllCamera = function() {
    $scope.allCamera = false;
    $window.localStorage.removeItem("camera")
    $window.location.reload()
  }

  function init() {
    ws.onmessage = function(e) {
      var parsed = JSON.parse(e.data),
          videoArr = [],sourceArr = [],
          localCam = $window.localStorage.getItem("camera");
      if(localCam) {
        parsed = parsed.filter(function(camInfo) {
          return camInfo.name == localCam;
        })
      }
      parsed = _.sortBy(parsed, function(obj){ return obj.name });
      $scope.cameraInfo = [];
      for(var i=0;i<parsed.length;i++) {
        if(!isEmpty(parsed[i])) {
          $scope.cameraInfo[i] = parsed[i];
          if(parsed[i].liveUrl) {
            $scope.cameraInfo[i].streamUrl = "http://" + window.location.hostname + ":" + parsed[i].liveUrl;
          }
          if(cameraStatus.length > 0) {
            _.each(cameraStatus, function(cameraSt, index) {
              if(i === index && $scope.cameraInfo[i].status === 3) {
                $scope.cameraInfo[index].disabled = true;
                $scope.cameraInfo[i].status = cameraSt == 1 ? 2 : 1;
              }
            })
          }
        }
      }
      $scope.$apply();
      if(reload_video) {
        $scope.ngRepeatFinished();
      }
      reload_video = true;
    };
  };

  init();

  $scope.changeChk = function(index, new_status, disableFlg) {
    if(disableFlg) {
      $scope.cameraInfo[index].disabled = true;
      $scope.cameraInfo[index].status = new_status == 1 ? 2 : 1;
      alert("Camera is busy, Please wait momentarily.");
    } else {
      cameraStatus[index] = new_status;
      var cameraInfo = $scope.cameraInfo[index];
      delete cameraInfo.disabled;
      var camInfo = Object.assign({}, cameraInfo);
      if(camInfo.streamUrl){
        delete camInfo.streamUrl;
      }
      cameraInfo.status = new_status;
      ws.send(JSON.stringify([camInfo]));
      $scope.cameraInfo[index].disabled = true;
      $scope.cameraInfo[index].status = new_status == 1 ? 2 : 1;
    }
  };

  $scope.cameraClick = function(camera) {
    $window.localStorage.setItem("camera", camera.name);
    var localCam = $window.localStorage.getItem("camera");
    $scope.allCamera = true;
    $scope.cameraInfo = $scope.cameraInfo.filter(function(camInfo) {
      return camInfo.name == localCam;
    });
    $scope.ngRepeatFinished();
  };

  function isEmpty(obj) {
    for (var prop in obj) {
      if (obj.hasOwnProperty(prop)) {
        return false;
      }
    }
    return true;
  };

  $scope.ngRepeatFinished = function() {
    var videoArr=[],sourceArr=[];
    for(var j=0;j<$scope.cameraInfo.length;j++) {
      if($scope.cameraInfo[j].streamUrl) {
        videoArr[j] = document.getElementById("video"+j);
        sourceArr[j] = document.getElementById("source"+j);
        var currentSrc = sourceArr[j].getAttribute('src');
        if(!currentSrc || currentSrc != $scope.cameraInfo[j].streamUrl) {
          sourceArr[j].setAttribute('src', $scope.cameraInfo[j].streamUrl);
          videoArr[j].load();
          videoArr[j].play();
        }
      }
    }
  };
}])

.directive('onFinishRender', function ($timeout) {
  return {
    restrict: 'A',
    link: function (scope, element, attr) {
      if (scope.$last) {
        $timeout(function () {
          scope.$eval(attr.onFinishRender);
        });
      }
    }
  }
});
