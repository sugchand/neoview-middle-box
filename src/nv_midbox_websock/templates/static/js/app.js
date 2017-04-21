'use strict'
angular.module('landingApp', [])
.controller('landingController', ['$scope', '$window', function($scope, $window) {
  var host = "ws://" + $window.location.host + "/userwebsocket",
  cameraStatus = [],
  ws = new WebSocket(host);
  ws.onmessage = function(e) {
    var parsed = JSON.parse(e.data);
    parsed = _.sortBy(parsed, function(obj){ return obj.name });
    $scope.cameraInfo = [];
    for(var i=0;i<parsed.length;i++) {
      if(!isEmpty(parsed[i])) {
        $scope.cameraInfo[i] = parsed[i];
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
  };

  $scope.changeChk = function(index, new_status, disableFlg) {
    if(disableFlg) {
      $scope.cameraInfo[index].disabled = true;
      $scope.cameraInfo[index].status = new_status == 1 ? 2 : 1;
      alert("Camera is busy, Please wait....");
    } else {
      cameraStatus[index] = new_status;
      var cameraInfo = $scope.cameraInfo[index];
      delete cameraInfo.disabled;
      cameraInfo.status = new_status;
      ws.send(JSON.stringify([cameraInfo]));
      $scope.cameraInfo[index].disabled = true;
      $scope.cameraInfo[index].status = new_status == 1 ? 2 : 1;
    }
  };

  function isEmpty(obj) {
    for (var prop in obj) {
      if (obj.hasOwnProperty(prop)) {
        return false;
      }
    }
    return true;
  };

}]);