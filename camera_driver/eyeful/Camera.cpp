// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include <CameraRemote_SDK.h>
#include <CrDefines.h>
#include <CrDeviceProperty.h>
#include <CrTypes.h>
#include <IDeviceCallback.h>
#include <fmt/format.h>
#include <fmt/ranges.h>
#define MAGIC_ENUM_RANGE_MIN 0
// this is the largest enum value for a property code, but it is smaller than the largest enum value
// in the Sony SDK magic_enum limts the range of enum values
#define MAGIC_ENUM_RANGE_MAX 0x0800
#include <magic_enum/magic_enum.hpp>

#include "eyeful/Camera.h"
#include "eyeful/ErrorString.h"
#include "logging/Logging.h"

namespace fs = std::filesystem;
namespace SDK = SCRSDK;
using namespace std::chrono_literals;

Camera::Camera(const SDK::ICrCameraObjectInfo* camera_info) {
  info_.reset(
      SDK::CreateCameraObjectInfo(
          camera_info->GetName(),
          camera_info->GetModel(),
          camera_info->GetUsbPid(),
          camera_info->GetIdType(),
          camera_info->GetIdSize(),
          camera_info->GetId(),
          camera_info->GetConnectionTypeName(),
          camera_info->GetAdaptorName(),
          camera_info->GetPairingNecessity()));

  std::string connection_type = toString(info_->GetConnectionTypeName());

  // I'm not sure what this ID is (it's not the serial num or anything else obvious)
  // It does seem to be unique and constant, which is good enough
  camera_id_ = reinterpret_cast<char*>(info_->GetId());
  if (connection_type == "IP") {
    network_info_ = parse_ip_info(info_->GetId(), info_->GetIdSize());
    log_id_ = network_info_.ip_string;
  } else if (connection_type.compare("USB") == 0) {
    log_id_ = camera_id_;
    EYEFUL_LOGD("({}) USB PID: {}", log_id_, info_->GetUsbPid());
  } else {
    EYEFUL_LOGF("Invalid camera connection");
  }
}
Camera::~Camera() {
  const auto finalize_status = SDK::ReleaseDevice(device_handle_);
  device_handle_ = 0; // clear
  if (CR_FAILED(finalize_status)) {
    EYEFUL_LOGW("({}) Failed to release device", log_id_);
  }
}

bool Camera::connect(SDK::CrSdkControlMode control_mode) {
  // The SDK default behavior is to have automatic reconnecting turned on. I'm turning it off
  // because I don't think we should be losing connection, and if we are I want to explicitly deal
  // with it

  switch (control_mode) {
    case SDK::CrSdkControlMode_Remote:
      EYEFUL_LOGI("({}) Connecting to the camera in Remote mode", log_id_);
      break;
    case SDK::CrSdkControlMode_ContentsTransfer:
      EYEFUL_LOGI("({}) Connecting to the camera in Content Transfer mode", log_id_);
      break;
    default:
      EYEFUL_LOGF("({}) Unknown mode connection type", log_id_);
      return false;
  }
  const auto err =
      SDK::Connect(info_.get(), this, &device_handle_, control_mode, SDK::CrReconnecting_OFF);
  if (CR_FAILED(err)) {
    EYEFUL_LOGE("({}) Camera connection request failed: {}", log_id_, err);
    return false;
  }
  EYEFUL_LOGI("({}) Camera connection requested", log_id_);
  return true;
}

bool Camera::disconnect() {
  const auto disconnect_status = SDK::Disconnect(device_handle_);
  if (CR_FAILED(disconnect_status)) {
    EYEFUL_LOGE("({}) Camera failed to disconnect", log_id_);
    return false;
  }
  return true;
}

Camera::NetworkInfo Camera::parse_ip_info(const unsigned char* buf, std::uint32_t size) {
  // based heavily on the sony SDK example app. This is all undocumented in the SDK API Refrence
  constexpr std::size_t MAC_ADDRESS_BYTE = 6;
  constexpr std::size_t CAMERA_NAME_LENGTH_MAX = 256;
  constexpr std::size_t CAMERA_DESC_LENGTH_MAX = 256;

  struct NetworkInfoRaw {
    CrInt32u id_size;
    CrInt32u ip_address;
    CrInt8u name[CAMERA_NAME_LENGTH_MAX];
    CrInt8u desc[CAMERA_DESC_LENGTH_MAX];
    CrInt8u MACaddress[MAC_ADDRESS_BYTE];
    CrInt32u urlsize;
  };
  NetworkInfo info;
  NetworkInfoRaw raw_info;
  const auto raw_info_size = sizeof(raw_info);
  if (raw_info_size > size) {
    EYEFUL_LOGE("Id buffer not sized properly, not setting network info");
    return info;
  }
  std::memcpy(&raw_info, buf, raw_info_size);
  info.ip_address = raw_info.ip_address;
  info.ip_string = std::to_string(raw_info.ip_address & 0x000000FF) + "." +
      std::to_string((raw_info.ip_address >> 8) & 0x000000FF) + "." +
      std::to_string((raw_info.ip_address >> 16) & 0x000000FF) + "." +
      std::to_string((raw_info.ip_address >> 24) & 0x000000FF);

  info.mac_string = fmt::format(
      "{:02x}", fmt::join(raw_info.MACaddress, raw_info.MACaddress + MAC_ADDRESS_BYTE, ":"));

  EYEFUL_LOGI("Camera MAC Address {}, IP Address: {}", info.mac_string, info.ip_string);
  return info;
}

std::string_view Camera::getLogId() {
  return std::string_view(log_id_);
}

std::string Camera::getCameraModel() {
#if defined(_UNICODE) || defined(UNICODE)
  std::string model = toString(info_->GetModel());
#else
  std::string model(info_->GetModel());
#endif
  return model;
}

std::optional<CrInt64u> Camera::getPropertyRaw(CrInt32u code) {
  // It would be nice if this was a unqiue_ptr, but the release get's tricky since we need to pass
  // the device handle. Until I figure out a good way to do this I'm using a raw pointer and trying
  // to be careful.
  if (!connected_) {
    return std::nullopt;
  }
  std::optional<CrInt64u> return_value = std::nullopt;
  SDK::CrDeviceProperty* prop_list = nullptr;
  std::int32_t nprop = 0;
  const auto err = SDK::GetSelectDeviceProperties(device_handle_, 1, &code, &prop_list, &nprop);
  if (CR_FAILED(err) || !prop_list || nprop <= 0) {
    EYEFUL_LOGE("({}) Failed to get device properties of {}", log_id_, crPropertyCodeString(code));
  } else {
    if (code == prop_list[0].GetCode()) {
      return_value = prop_list[0].GetCurrentValue();
    } else {
      EYEFUL_LOGW("({}) Unexpected return code from GetSelectDeviceProperties", log_id_);
    }
  }
  SDK::ReleaseDeviceProperties(device_handle_, prop_list);
  return return_value;
}

bool Camera::propertyCheckSetValue(CrInt32u code, const CrInt64u value) {
  // check if a camera property is set with a given value
  const auto property_raw = getPropertyRaw(code);
  if (property_raw) {
    return property_raw == value;
  } else {
    EYEFUL_LOGW(
        "({}) Invalid return from getPropertyRaw, can not check value, returning False", log_id_);
    return false;
  }
}

bool Camera::setPropertyRaw(const CrInt32u code, const CrInt64u value, const SDK::CrDataType type) {
  if (!connected_) {
    EYEFUL_LOGE("NOT CONNECTED. NOT SETTING PROPERTY");
    return false;
  }
  SDK::CrDeviceProperty property;
  property.SetCode(code);
  property.SetCurrentValue(value);
  property.SetValueType(type);
  // Device settings are updated asynchronously; all the return of SetDeviceProperty tells us is
  // if the command was sent out, not if it was applied by the camera successfully
  const auto err = SDK::SetDeviceProperty(device_handle_, &property);
  if (CR_FAILED(err)) {
    EYEFUL_LOGE(
        "({}) Failed to set property {}: {}",
        log_id_,
        crPropertyCodeString(code),
        error2string::decode(err));
    return false;
  }
  return true;
}

void Camera::ClearPropertyPromise(CrInt32u code) {
  property_promises_mutex_.lock();
  property_promises_.erase(code);
  property_promises_mutex_.unlock();
}

std::optional<std::future<void>>
Camera::setPropertyAsync(const CrInt32u code, const CrInt64u value, const SDK::CrDataType type) {
  // return a future that will be fulfilled once the property has been set, or a null optional if
  // there's an error

  property_promises_mutex_.lock();

  if (property_promises_.find(code) != property_promises_.end()) {
    // If there is an existing promise for this property we should not start a new one
    // Whoever requested the property set is responsible for cleaning up the property list when the
    // promise is fullfilled or if they've decided it failed
    EYEFUL_LOGW(
        "({}) Setting property {} already in progress, wait for it to finish before setting again",
        log_id_,
        crPropertyCodeString(code));
    property_promises_mutex_.unlock();
    return std::nullopt;
  }

  std::promise<void> promise;
  property_promises_.insert({code, std::move(promise)});
  property_promises_mutex_.unlock();

  // Check if the value is already set, if it's not then set it
  if (propertyCheckSetValue(code, value)) {
    property_promises_mutex_.lock();
    property_promises_[code].set_value();
    property_promises_mutex_.unlock();
  } else {
    if (!setPropertyRaw(code, value, type)) {
      ClearPropertyPromise(code);
      return std::nullopt;
    }
  }

  return property_promises_[code].get_future();
}

bool Camera::setProperty(const CrInt32u code, const CrInt64u value, const SDK::CrDataType type) {
  auto property_future = setPropertyAsync(code, value, type);
  if (!property_future.has_value()) {
    return false;
  }
  // Setting a property can take 100s of milliseconds, but I haven't done much work timing it
  // This timeout is set high so we have confidence that if we hit it something has gone horribly
  // wrong
  const auto timeout = 1500ms;
  const auto future_status = property_future->wait_for(timeout);
  ClearPropertyPromise(code);

  if (future_status != std::future_status::ready) {
    EYEFUL_LOGW(
        "({}) Timed out at {}ms waiting for property {} to set",
        log_id_,
        timeout.count(),
        crPropertyCodeString(code));
    return false;
  }

  if (!propertyCheckSetValue(code, value)) {
    EYEFUL_LOGE("({}) Property {} did not set correctly", log_id_, crPropertyCodeString(code));
    return false;
  }

  return true;
}

std::string Camera::crPropertyCodeString(const CrInt32u code) {
  const auto enum_value = magic_enum::enum_cast<SDK::CrDevicePropertyCode>(code);
  if (enum_value.has_value()) {
    return std::string{magic_enum::enum_name(enum_value.value())};
  } else {
    EYEFUL_LOGW("enum cast of {0:#x} to CrDeviceProperty failed", code);
    return "";
  }
}

bool Camera::setPcPriority() {
  // Need to set the camera to use SDK settings over the dials
  const auto success = setProperty(
      SDK::CrDevicePropertyCode::CrDeviceProperty_PriorityKeySettings,
      SDK::CrPriorityKeySettings::CrPriorityKey_PCRemote,
      SDK::CrDataType::CrDataType_UInt32Array);
  return success;
}

bool Camera::setDriveMode(CrInt64u mode) {
  const auto success = setProperty(
      SDK::CrDevicePropertyCode::CrDeviceProperty_DriveMode,
      mode,
      SDK::CrDataType::CrDataType_UInt32Array);
  return success;
}

bool Camera::isConnected() {
  return connected_;
}

bool Camera::setShutterSpeed(CrInt64u speed) {
  // the speed here is the Sony API speed number
  // See the "CrDeviceProperty_ShutterSpeed" section in the SDK document for a description
  // TLDR 32bit number, top two bytes are 10x the numerator and the bottom two are the denominator
  const auto success = setProperty(
      SDK::CrDevicePropertyCode::CrDeviceProperty_ShutterSpeed,
      speed,
      SDK::CrDataType::CrDataType_UInt32Array);
  return success;
}

CrInt64u Camera::string2speed(std::string speed) {
  // return Sony API speed number, or 0 on error
  uint32_t numerator = 0;
  uint32_t denominator = 0;
  if (speed.compare("BULB") == 0) {
    EYEFUL_LOGD("BULB exposure");
    return SDK::CrShutterSpeedSet::CrShutterSpeed_Bulb;
  }
  auto slash_position = speed.find("/");
  if (slash_position != std::string::npos) {
    numerator = 0x1; // using hex notation to mirror Sony's documentation
    try {
      denominator = std::stoul(speed.substr(slash_position + 1), nullptr, 10);
    } catch (const std::invalid_argument& e1) {
      EYEFUL_LOGE("Invalid shutter speed string {}", speed);
      return 0;
    }
  } else {
    // the camera shows " after non fraction speeds
    if (speed.back() == '"') {
      speed.pop_back();
    }
    try {
      numerator = static_cast<uint16_t>(std::stof(speed, nullptr) * 10);
    } catch (const std::invalid_argument& e1) {
      EYEFUL_LOGE("Invalid shutter speed string {}", speed);
      return 0;
    }
    denominator = 0xA;
  }
  CrInt64u SDKspeed = (numerator << 16) + denominator;
  EYEFUL_LOGD("{} is {:#x}", speed, SDKspeed);
  return SDKspeed;
}

std::string Camera::speed2string(CrInt64u speed) {
  std::string output;

  if (speed == SDK::CrShutterSpeedSet::CrShutterSpeed_Bulb) {
    return "BULB";
  }

  uint32_t numerator = (speed >> 16) & 0xFFFF;
  uint32_t denominator = speed & 0xFFFF;

  if (numerator == 0x1) {
    output = "1/" + std::to_string(denominator);
  } else if (denominator == 0xA) {
    output = std::to_string(numerator / 10.0) + "\"";
  } else {
    output = "invalid";
    EYEFUL_LOGE("Invalid shutter speed {:#x}", speed);
  }

  return output;
}

std::optional<std::future<bool>> Camera::quickFormatMedia(MediaSlot slot) {
  // From testing if you send a quick format command while a quick format is in progress the
  // camera starts a new format as soon as the running one finishes
  SDK::CrDevicePropertyCode property_code;
  if (slot == MediaSlot::SLOT1) {
    property_code = SDK::CrDevicePropertyCode::CrDeviceProperty_MediaSLOT1_QuickFormatEnableStatus;
  } else if (slot == MediaSlot::SLOT2) {
    property_code = SDK::CrDevicePropertyCode::CrDeviceProperty_MediaSLOT2_QuickFormatEnableStatus;
  } else {
    EYEFUL_LOGE("({}) Invalid media slot selection {}", log_id_, magic_enum::enum_name(slot));
    return std::nullopt;
  }
  // I don't know what causes quick format to be unavailable
  if (!propertyCheckSetValue(property_code, SDK::CrMediaFormat::CrMediaFormat_Enable)) {
    EYEFUL_LOGW("({}) {} quick format is not enabled", log_id_, magic_enum::enum_name(slot));
    return std::nullopt;
  }
  std::promise<bool>().swap(format_completed_);
  // This could be superstitious, but I want to insure the future is created before sending the
  // command, so we can't miss the response
  std::future<bool> format_future = format_completed_.get_future();
  const auto out = SDK::SendCommand(
      device_handle_,
      SDK::CrCommandId::CrCommandId_MediaQuickFormat,
      static_cast<SDK::CrCommandParam>(slot));
  if (CR_FAILED(out)) {
    EYEFUL_LOGE("({}) Failed to quick format {}", log_id_, magic_enum::enum_name(slot));
    return std::nullopt;
  }
  return format_future;
}

std::optional<std::future<bool>> Camera::formatMedia(MediaSlot slot) {
  SDK::CrDevicePropertyCode property_code;
  if (slot == MediaSlot::SLOT1) {
    property_code = SDK::CrDevicePropertyCode::CrDeviceProperty_MediaSLOT1_FormatEnableStatus;
  } else if (slot == MediaSlot::SLOT2) {
    property_code = SDK::CrDevicePropertyCode::CrDeviceProperty_MediaSLOT2_FormatEnableStatus;
  } else {
    EYEFUL_LOGE("({}) Invalid media slot selection {}", log_id_, magic_enum::enum_name(slot));
    return std::nullopt;
  }

  if (!propertyCheckSetValue(property_code, SDK::CrMediaFormat::CrMediaFormat_Enable)) {
    EYEFUL_LOGW("({}) {} format is not enabled", log_id_, magic_enum::enum_name(slot));
    return std::nullopt;
  }

  std::promise<bool>().swap(format_completed_);
  // This could be superstitious, but I want to insure the future is created before sending the
  // command, so we can't miss the response
  std::future<bool> format_future = format_completed_.get_future();
  const auto out = SDK::SendCommand(
      device_handle_,
      SDK::CrCommandId::CrCommandId_MediaFormat,
      static_cast<SDK::CrCommandParam>(slot));
  if (CR_FAILED(out)) {
    EYEFUL_LOGE("({}) Failed to format {}", log_id_, magic_enum::enum_name(slot));
    return std::nullopt;
  }
  return format_future;
}

bool Camera::shutterButtonDown() {
  exposures_.store(0);
  const auto out = SDK::SendCommand(
      device_handle_, SDK::CrCommandId::CrCommandId_Release, SDK::CrCommandParam_Down);
  if (CR_FAILED(out)) {
    return false;
  }
  return true;
}

bool Camera::shutterButtonUp() {
  const auto out = SDK::SendCommand(
      device_handle_, SDK::CrCommandId::CrCommandId_Release, SDK::CrCommandParam_Up);
  if (CR_FAILED(out)) {
    return false;
  }
  return true;
}

bool Camera::takeImage() {
  auto out = shutterButtonDown();
  // sleep time used by the Sony example application
  std::this_thread::sleep_for(std::chrono::milliseconds(35));
  out &= shutterButtonUp();
  return out;
}

unsigned short int Camera::exposures() {
  return exposures_.load();
}

std::optional<Camera::IsoInfo> Camera::getIso() {
  const auto iso_raw = getPropertyRaw(SDK::CrDevicePropertyCode::CrDeviceProperty_IsoSensitivity);
  if (!iso_raw) {
    return std::nullopt;
  }

  // I don't understand what ISO extension is for. If we figure that out this is how you get it:
  // std::uint32_t iso_extension = (iso_raw.value() >> 24) & 0x000000F0; // bit 28-31
  std::uint32_t iso_mode = (iso_raw.value() >> 24) & 0x0000000F; // bit 24-27
  std::uint32_t iso_value = (iso_raw.value() & 0x00FFFFFF); // bit  0-23

  Camera::IsoInfo output;

  switch (iso_mode) {
    case SDK::CrISOMode::CrISO_Normal: {
      output.iso_mode = SDK::CrISOMode::CrISO_Normal;
      break;
    }
    case SDK::CrISOMode::CrISO_MultiFrameNR: {
      output.iso_mode = SDK::CrISOMode::CrISO_MultiFrameNR;
      break;
    }
    case SDK::CrISOMode::CrISO_MultiFrameNR_High: {
      output.iso_mode = SDK::CrISOMode::CrISO_MultiFrameNR_High;
      break;
    }
    default: {
      EYEFUL_LOGW("({}) Undefined ISO Mode", log_id_);
      return std::nullopt;
    }
  }

  if (iso_value == SDK::CrISOMode::CrISO_AUTO) {
    output.iso_auto = true;
  } else {
    output.iso_value = iso_value;
  }

  return output;
}

bool Camera::setIso(Camera::IsoInfo iso_info) {
  if (iso_info.iso_auto) {
    if (iso_info.iso_value != 0 && iso_info.iso_value != SDK::CrISOMode::CrISO_AUTO) {
      EYEFUL_LOGI("ISO value set when Auto is true. Setting the ISO value to Auto");
    }
    iso_info.iso_value = SDK::CrISOMode::CrISO_AUTO;
  }
  CrInt64u formated_iso = (iso_info.iso_mode << 24) | iso_info.iso_value;
  const auto success = setProperty(
      SDK::CrDevicePropertyCode::CrDeviceProperty_IsoSensitivity,
      formated_iso,
      SDK::CrDataType::CrDataType_UInt32Array);
  return success;
}

bool Camera::setAperture(float fvalue) {
  // This function expects the f-value to be passed as it's displayed on the camera. Ex f/8 == 8.0
  // not 1/8.0
  EYEFUL_CHECK(
      (fvalue > 100), "Invalid F-value. Please enter the F-Value as it appears on the camera");
  EYEFUL_CHECK((fvalue < 0), "F-value can not be negative");
  const int FVALUE_SCALE_FACTOR = 100; // scale factor from the SDK docs
  const auto success = setProperty(
      SDK::CrDevicePropertyCode::CrDeviceProperty_FNumber,
      static_cast<uint16_t>(
          fvalue *
          FVALUE_SCALE_FACTOR), // input validation protects us from negative numbers and overflow
      SDK::CrDataType::CrDataType_UInt16Array);
  return success;
}

std::optional<std::future<bool>> Camera::setDateTimeAsync() {
  auto now = std::chrono::system_clock::now();
  uint64_t utc_time = static_cast<uint64_t>(
      std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count());

  std::promise<bool>().swap(date_time_completed_);
  std::future<bool> date_time_future = date_time_completed_.get_future();

  const auto success = setPropertyRaw(
      SDK::CrDevicePropertyCode::CrDeviceProperty_DateTime_Settings,
      utc_time,
      SDK::CrDataType::CrDataType_UInt64);
  if (!success) {
    EYEFUL_LOGE("({}) Failed to send DateTime", log_id_);
    return std::nullopt;
  }
  return date_time_future;
}

bool Camera::setDateTime() {
  auto date_time_future = setDateTimeAsync();
  if (!date_time_future) {
    return false;
  }

  // a made up timeout
  const auto timeout = 1500ms;
  const auto future_status = date_time_future->wait_for(timeout);

  if (future_status != std::future_status::ready) {
    EYEFUL_LOGW("({}) Timed out at {}ms waiting for DateTime to set", log_id_, timeout.count());
    return false;
  }

  if (!date_time_future->get()) {
    EYEFUL_LOGE("({}) DateTime setting failed", log_id_);
    return false;
  }

  return true;
}

void Camera::OnConnected(SDK::DeviceConnectionVersioin version) {
  EYEFUL_LOGI("({}) Camera Connected. Version: {}", log_id_, magic_enum::enum_name(version));
  connected_.store(true);
}

void Camera::OnDisconnected(CrInt32u error) {
  EYEFUL_LOGI("({}) Camera disconnected. Error: {}", log_id_, error);
  connected_.store(false);
}

void Camera::OnPropertyChanged() {}

void Camera::OnPropertyChangedCodes(CrInt32u num, CrInt32u* codes) {
  // We're assuming that there are few enough changed properties and outstanding promisies that
  // we'll make it out of this call back fast
  property_promises_mutex_.lock();
  for (CrInt32u i = 0; i < num; ++i) {
    if (property_promises_.find(codes[i]) != property_promises_.end()) {
      // all we know here is that the property we care about changed
      // we need to check somewhere else that it's changed to the value we want
      property_promises_[codes[i]].set_value();
    }
  }
  property_promises_mutex_.unlock();
}

void Camera::OnLvPropertyChanged() {}

void Camera::OnLvPropertyChangedCodes(CrInt32u, CrInt32u*) {}

void Camera::OnCompleteDownload(CrChar*, CrInt32u) {}

void Camera::OnNotifyContentsTransfer(CrInt32u, SDK::CrContentHandle, CrChar* filename) {
  if (filename != nullptr) {
    std::string filename_str = toString(filename);
    EYEFUL_LOGI("({}) Download completed: {}", log_id_, filename_str);
  }
}

void Camera::OnWarning(CrInt32u warning) {
  switch (warning) {
    case SDK::CrWarning_Reserved1: {
      EYEFUL_LOGT("({}) {}", log_id_, error2string::decode(warning));
      break;
    }
    case SDK::CrWarning_Reserved5: {
      // Our sony contact told us it's safe to ignore this warning
      EYEFUL_LOGT("({}) {}", log_id_, error2string::decode(warning));
      break;
    }
    case SDK::CrNotify_Captured_Event: {
      // The API documentation I have says that the Sony A1 does not support this capture
      // notification, however I'm recieving it from cameras running firmware v1.2 and higher
      EYEFUL_LOGD("({}) {}", log_id_, error2string::decode(warning));
      exposures_++;
      break;
    }
    case SDK::CrWarning_Format_Failed: {
      EYEFUL_LOGE("({}) {}", log_id_, error2string::decode(warning));
      format_completed_.set_value(false);
      break;
    }
    case SDK::CrWarning_Format_Invalid: {
      EYEFUL_LOGE("({}) {}", log_id_, error2string::decode(warning));
      format_completed_.set_value(false);
      break;
    }
    case SDK::CrWarning_Format_Complete: {
      EYEFUL_LOGD("({}) {}", log_id_, error2string::decode(warning));
      format_completed_.set_value(true);
      break;
    }
    case SDK::CrWarning_Format_Canceled: {
      EYEFUL_LOGW("({}) {}", log_id_, error2string::decode(warning));
      format_completed_.set_value(false);
      break;
    }
    // DateTime goes through warnings instead of the normal PropertyChangedCodes
    case SDK::CrWarning_DateTime_Setting_Result_OK: {
      EYEFUL_LOGD("({}) {}", log_id_, error2string::decode(warning));
      date_time_completed_.set_value(true);
      break;
    }
    case SDK::CrWarning_DateTime_Setting_Result_Invalid: {
      EYEFUL_LOGD("({}) {}", log_id_, error2string::decode(warning));
      date_time_completed_.set_value(false);
      break;
    }
    case SDK::CrWarning_DateTime_Setting_Result_Parameter_Error: {
      EYEFUL_LOGD("({}) {}", log_id_, error2string::decode(warning));
      date_time_completed_.set_value(false);
      break;
    }
    case SDK::CrWarning_DateTime_Setting_Result_Exclusion_Error: {
      EYEFUL_LOGD("({}) {}", log_id_, error2string::decode(warning));
      date_time_completed_.set_value(false);
      break;
    }
    case SDK::CrWarning_DateTime_Setting_Result_System_Error: {
      EYEFUL_LOGD("({}) {}", log_id_, error2string::decode(warning));
      date_time_completed_.set_value(false);
      break;
    }
    case SDK::CrWarning_NetworkErrorOccurred: {
      EYEFUL_LOGW("({}) {}: Disconnected from camera.", log_id_, error2string::decode(warning));
      connected_.store(false);
      break;
    }
    default: {
      EYEFUL_LOGW("({}) {}", log_id_, error2string::decode(warning));
    }
  }
}

void Camera::OnWarningExt(CrInt32u, CrInt32, CrInt32, CrInt32) {}

void Camera::OnError(CrInt32u error) {
  if (FATAL_ERRORS_.find(error) != FATAL_ERRORS_.end()) {
    EYEFUL_LOGF("({}) {}", log_id_, error2string::decode(error));
  } else {
    EYEFUL_LOGE("({}) {}", log_id_, error2string::decode(error));
  }
}

std::string Camera::toString(char* value) {
  return value;
}
#if defined(_UNICODE) || defined(UNICODE)
std::string Camera::toString(wchar_t* value) {
  // Note: wchar_t* conversion to string will only work for ASCII characters
  std::wstring value_ws(value);
  std::string value_string(value_ws.begin(), value_ws.end());
  return value_string;
}
#endif

bool Camera::transferFiles(const std::string& root_path) {
  EYEFUL_LOGI("({}) Starting transfers...", log_id_);
  // If a camera is connected via ethernet, the log id will be its IP address
  // the id if its a USB is alpha numeric and unique
  std::string camera_dir = log_id_;
  if (log_id_.find('.') != std::string::npos) {
    camera_dir = log_id_.substr(log_id_.length() - 2, 2);
  }
  const fs::path output_path = fs::path(root_path) / camera_dir;

  SDK::CrMtpFolderInfo* folder_info = nullptr;
  CrInt32u num_folders = 0;

  if (auto out = SDK::GetDateFolderList(device_handle_, &folder_info, &num_folders);
      CR_FAILED(out)) {
    EYEFUL_LOGE("({}) Failed to get folders.", log_id_);
    OnError(out);
    return false;
  }
  EYEFUL_LOGI("({}) Found {} folder(s)", log_id_, num_folders);

  for (CrInt32u i = 0; i < num_folders; ++i) {
    const auto& folder = folder_info[i];
    SDK::CrContentHandle* contentsHandles = nullptr;
    CrInt32u num_contents = 0;

    while (true) {
      auto out = SDK::GetContentsHandleList(
          device_handle_, folder.handle, &contentsHandles, &num_contents);
      // CrError_Contents_RejectRequest is returned by the SDK during content
      // transfer process.
      if (out == SDK::CrError_Contents_RejectRequest) {
        EYEFUL_LOGI("({}) Waiting for contents handle...", log_id_);
        using namespace std::chrono_literals;
        std::this_thread::sleep_for(1s);
        continue;
      }

      if (CR_FAILED(out)) {
        EYEFUL_LOGE("({}) Failed to get content handles.", log_id_);
        SDK::ReleaseDateFolderList(device_handle_, folder_info);
        OnError(out);
        return false;
      } else {
        break;
      }
    }

    EYEFUL_LOGI("({}) Found {} content(s)", log_id_, num_contents);

    CrInt32u progress_tracker = 0;
    // Defines how many progress updates are made
    // E.g., 20 corresponds to 20 progress updates sent to console
    const CrInt32u progress_display_amounts = 20;
    const CrInt32u progress_num_files = num_contents / progress_display_amounts;

    for (CrInt32u j = 0; j < num_contents; ++j) {
      if ((j - progress_tracker) >= progress_num_files) {
        EYEFUL_LOGI("({}) Completed {} file transfers out of {}", log_id_, j, num_contents);
        progress_tracker = j;
      }

      auto content_handle = contentsHandles[j];
      SDK::CrMtpContentsInfo content_info;

      // This needs called before PullContentsFile
      auto out = SDK::GetContentsDetailInfo(device_handle_, content_handle, &content_info);
      if (CR_FAILED(out)) {
        OnError(out);
        SDK::ReleaseContentsHandleList(device_handle_, contentsHandles);
        SDK::ReleaseDateFolderList(device_handle_, folder_info);
        return false;
      }

#if defined(_UNICODE) || defined(UNICODE)
      const wchar_t* output_wchar = output_path.c_str();
      std::vector<wchar_t> output_path_vec(output_wchar, output_wchar + wcslen(output_wchar) + 1);
#else
      const char* output_char = output_path.c_str();
      std::vector<char> output_path_vec(output_char, output_char + strlen(output_char) + 1);
#endif

      auto full_file_path = output_path / content_info.fileName;
      if (!std::filesystem::exists(full_file_path)) {
        // Starting the transfer
        out = SDK::PullContentsFile(
            device_handle_,
            content_handle,
            SDK::CrPropertyStillImageTransSize_Original,
            output_path_vec.data());
        if (CR_FAILED(out)) {
          OnError(out);
          SDK::ReleaseContentsHandleList(device_handle_, contentsHandles);
          SDK::ReleaseDateFolderList(device_handle_, folder_info);
          return false;
        }

        // Wait for the transfer to finish...
        while (true) {
          auto out = SDK::GetContentsDetailInfo(device_handle_, content_handle, &content_info);
          if (out == SDK::CrError_Contents_RejectRequest) {
            // CrError_Contents_RejectRequest is an error code returned during the
            // fetching process, it means the SDK is still working on the call
            EYEFUL_LOGI("({}) Waiting for contents details...{}", log_id_, j);
            using namespace std::chrono_literals;
            std::this_thread::sleep_for(3s);
            continue;
          }
          if (CR_FAILED(out)) {
            OnError(out);
            SDK::ReleaseContentsHandleList(device_handle_, contentsHandles);
            SDK::ReleaseDateFolderList(device_handle_, folder_info);
            return false;
          } else {
            break;
          }
        }
      } else {
#ifdef _WIN32
        EYEFUL_LOGW("({}) Skipping {} already exists", log_id_, full_file_path.string());
#else
        EYEFUL_LOGW("({}) Skipping {} already exists", log_id_, full_file_path.c_str());
#endif
      }
    }
    SDK::ReleaseContentsHandleList(device_handle_, contentsHandles);
  }
  SDK::ReleaseDateFolderList(device_handle_, folder_info);
  EYEFUL_LOGI("({}) Finished transferring", log_id_);

  return true;
}
