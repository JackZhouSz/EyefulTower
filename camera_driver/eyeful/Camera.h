// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <atomic>
#include <cstdint>
#include <future>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <unordered_set>

#include <CameraRemote_SDK.h>
#include <CrTypes.h>
#include <IDeviceCallback.h>

class Camera : public SCRSDK::IDeviceCallback {
 public:
  Camera();
  explicit Camera(const SCRSDK::ICrCameraObjectInfo* camera_info);
  virtual ~Camera();

  enum class MediaSlot {
    SLOT1 = SCRSDK::CrCommandParam_Up,
    SLOT2 = SCRSDK::CrCommandParam_Down,
  };

  struct IsoInfo {
    bool iso_auto = false;
    SCRSDK::CrISOMode iso_mode;
    int iso_value = 0;
  };

  bool connect(SCRSDK::CrSdkControlMode control_mode = SCRSDK::CrSdkControlMode_Remote);
  bool disconnect();
  bool shutterButtonDown();
  bool shutterButtonUp();
  bool takeImage();
  bool setPcPriority();
  bool setDriveMode(CrInt64u mode);
  bool isConnected();
  // this method should probably be private. A lot of the properties need converted from the
  // CrInt64u to make sense even the ones that don't should probably be returned as a more
  // appropriate type. I'm leaving it here for the moment because it is pretty helpful for debug
  std::optional<CrInt64u> getPropertyRaw(CrInt32u code);
  unsigned short int exposures();
  std::optional<std::future<bool>> quickFormatMedia(MediaSlot slot);
  std::optional<std::future<bool>> formatMedia(MediaSlot slot);
  std::string_view getLogId();
  std::string getCameraModel();
  bool setShutterSpeed(CrInt64u speed);
  static CrInt64u string2speed(std::string speed);
  static std::string speed2string(CrInt64u speed);
  std::optional<Camera::IsoInfo> getIso();
  bool setIso(Camera::IsoInfo iso_info);
  bool setAperture(float fvalue);
  bool transferFiles(const std::string& root_path);
  std::optional<std::future<void>>
  setPropertyAsync(CrInt32u code, CrInt64u value, SCRSDK::CrDataType type);
  bool setProperty(CrInt32u code, CrInt64u value, SCRSDK::CrDataType type);
  void ClearPropertyPromise(CrInt32u code);
  std::optional<std::future<bool>> setDateTimeAsync();
  bool setDateTime();

 private:
  struct NetworkInfo {
    std::uint32_t ip_address = 0;
    std::string ip_string;
    std::string mac_string;
  };
  bool setPropertyRaw(CrInt32u code, CrInt64u value, SCRSDK::CrDataType type);
  bool propertyCheckSetValue(CrInt32u code, CrInt64u value);
  std::string crPropertyCodeString(CrInt32u code);
  NetworkInfo parse_ip_info(const unsigned char* buf, std::uint32_t size);
  // Inherited via IDeviceCallback
  virtual void OnConnected(SCRSDK::DeviceConnectionVersioin version) override;
  virtual void OnDisconnected(CrInt32u error) override;
  virtual void OnPropertyChanged() override;
  virtual void OnLvPropertyChanged() override;
  virtual void OnCompleteDownload(CrChar* filename, CrInt32u type) override;
  virtual void OnWarning(CrInt32u warning) override;
  virtual void OnError(CrInt32u error) override;
  virtual void OnPropertyChangedCodes(CrInt32u num, CrInt32u* codes) override;
  virtual void OnLvPropertyChangedCodes(CrInt32u num, CrInt32u* codes) override;
  virtual void OnNotifyContentsTransfer(
      CrInt32u notify,
      SCRSDK::CrContentHandle contentHandle,
      CrChar* filename = 0) override;
  std::string toString(char* value);
  virtual void OnWarningExt(CrInt32u warning, CrInt32 param1, CrInt32 param2, CrInt32 param3)
      override;
#if defined(_UNICODE) || defined(UNICODE)
  std::string toString(wchar_t* value);
#endif

  struct CameraObjectInfoDeleter {
    void operator()(SCRSDK::ICrCameraObjectInfo* p) {
      if (p) {
        p->Release();
      }
    }
  };

  NetworkInfo network_info_;
  std::string camera_id_{""};
  std::string log_id_{""};
  std::atomic<bool> connected_{false};
  std::int64_t device_handle_{0};
  std::unique_ptr<SCRSDK::ICrCameraObjectInfo, CameraObjectInfoDeleter> info_;
  std::atomic<unsigned short int> exposures_{0};
  std::promise<bool> format_completed_;
  std::promise<bool> date_time_completed_;
  std::map<CrInt32u, std::promise<void>> property_promises_;
  std::mutex property_promises_mutex_;

  // it's possible we could figure out ways to recover from some of these
  // CrError_Connect_Timeout is the only one I've seen in the wild
  const std::unordered_set<CrInt32> FATAL_ERRORS_{
      SCRSDK::CrError_Connect_TimeOut,
      SCRSDK::CrError_Connect_FailRejected,
      SCRSDK::CrError_Connect_FailBusy,
      SCRSDK::CrError_Connect_FailUnspecified};
};
