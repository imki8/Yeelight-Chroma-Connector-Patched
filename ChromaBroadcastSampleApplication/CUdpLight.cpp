/*
 *Copyright (c) 2021, Yeelight
 *All rights reserved.
 *
 *Redistribution and use in source and binary forms, with or without
 *modification, are permitted provided that the following conditions are met:
 *
 *1. Redistributions of source code must retain the above copyright notice, this
 *   list of conditions and the following disclaimer.
 *
 *2. Redistributions in binary form must reproduce the above copyright notice,
 *   this list of conditions and the following disclaimer in the documentation
 *   and/or other materials provided with the distribution.
 *
 *3. Neither the name of the copyright holder nor the names of its
 *   contributors may be used to endorse or promote products derived from
 *   this software without specific prior written permission.
 */

#include "stdafx.h"
#include "CUdpLight.h"
//#include <json/json.h>


CUdpLight::CUdpLight()
{
	memset(cModel, 0, sizeof(cModel));
	memset(cDID, 0, sizeof(cDID));
	memset(cIP, 0, sizeof(cIP));
	memset(cToken, 0, sizeof(cToken));
	msg_id = 1;
	iPort = 0;
	ucBright = 100;
	SwitchStatus = 0;//default status on
	bAllowCtrlFlag = TRUE;
	bConnectStat = FALSE;
	cMappingLED = 1;
	iSendKplCount = 0;
	udp_light_state = UDP_STATE_IDLE;
	memset(cSupport, 0, sizeof(cSupport));
	cProtocolVer = 1;
	cDeviceType = 0;
	PreviewIngFlag = 0;
}

CUdpLight::~CUdpLight()
{
}


void CUdpLight::OnClose(int nErrorCode)
{
	if (nErrorCode == 0)
	{
		;
	}
	CAsyncSocket::OnClose(nErrorCode);
}



void CUdpLight::OnOutOfBandData(int nErrorCode)
{
	CAsyncSocket::OnOutOfBandData(nErrorCode);
}


void CUdpLight::OnReceive(int nErrorCode)
{
	if (nErrorCode == 0)
	{
		char pBuf[1025] = {0};

		int iLen = 0;
		SOCKADDR fromSocket;
		int addrLen = sizeof(SOCKADDR);
		iLen = this->ReceiveFrom(pBuf, 1024, &fromSocket, &addrLen, 0);
		if (iLen == SOCKET_ERROR)
		{
			printf("recv:%s\r\n", pBuf);
		}
		else
		{
			ProcRecvData(pBuf);
			printf("recv:%s\r\n", pBuf);
		}
	}
	CAsyncSocket::OnReceive(nErrorCode);
}


void CUdpLight::OnSend(int nErrorCode)
{
	CAsyncSocket::OnSend(nErrorCode);
}


void CUdpLight::OnConnect(int nErrorCode)
{
	if (nErrorCode == 0)
	{
		// TCP connection established — mark as ready immediately
		this->udp_light_state = UDP_STATE_CONNECTED;
		this->iSendKplCount = 0;
	}
	CAsyncSocket::OnConnect(nErrorCode);
}

void CUdpLight::ProcRecvData(char* recv_data)
{
	// Standard Yeelight LAN protocol — no token handshake needed
}

bool CUdpLight::AcquireToken()
{
	// TCP connection is established asynchronously via OnConnect.
	// Nothing to do here.
	return true;
}


void CUdpLight::SendKplMsg()
{
	// Keep-alive not needed for standard TCP Yeelight LAN protocol
}

bool CUdpLight::IsAllowedSendCtrlMsg()
{
	if (this->bConnectStat != TRUE)
	{
		return false;
	}

	if (this->bAllowCtrlFlag != TRUE)
	{
		return false;
	}

	if (this->PreviewIngFlag == 1)
	{
		return false;
	}

	return true;
}


void CUdpLight::SendCtrlMsgSwitchPower(bool SwitchStatus, char* effect, int duration)
{
	char sendBuf[200];
	int len;

	if (this->SwitchStatus == 1)
	{
		return;
	}

	len = snprintf(sendBuf, sizeof(sendBuf),
		"{\"id\":%d,\"method\":\"set_power\",\"params\":[\"off\",\"%s\",%d]}\r\n",
		this->msg_id, effect, duration);

	this->SwitchStatus = 1;
	this->Send(sendBuf, len, 0);

	if (this->msg_id++ < 0) this->msg_id = 1;
}

//{"id":1,"method":"set_rgb","params":[16711680,"smooth",200]}
void CUdpLight::SendCtrlMsgSetScene(COLORREF color, int bright, char* effect, int duration)
{
	char sendBuf[300];
	int len;

	// Convert COLORREF (BGR) to RGB integer
	int r = GetRValue(color);
	int g = GetGValue(color);
	int b = GetBValue(color);
	int rgb = (r << 16) | (g << 8) | b;

	// First ensure the lamp is on
	if (this->SwitchStatus == 1)
	{
		char powerBuf[200];
		int powerLen = snprintf(powerBuf, sizeof(powerBuf),
			"{\"id\":%d,\"method\":\"set_power\",\"params\":[\"on\",\"sudden\",0]}\r\n",
			this->msg_id);
		this->Send(powerBuf, powerLen, 0);
		if (this->msg_id++ < 0) this->msg_id = 1;
		this->SwitchStatus = 0;
	}

	// Set color using set_rgb
	len = snprintf(sendBuf, sizeof(sendBuf),
		"{\"id\":%d,\"method\":\"set_rgb\",\"params\":[%d,\"%s\",%d]}\r\n",
		this->msg_id, rgb, effect, duration);

	this->Send(sendBuf, len, 0);

	if (this->msg_id++ < 0) this->msg_id = 1;
}

void CUdpLight::SendCtrlMsgPreview()
{
	char sendBuf[300];
	int len;

	// Flash red then blue as a preview
	len = snprintf(sendBuf, sizeof(sendBuf),
		"{\"id\":%d,\"method\":\"start_cf\",\"params\":[4,0,\"500,1,16711680,100,500,1,255,100,500,1,65280,100,500,1,16776960,100\"]}\r\n",
		this->msg_id);

	this->Send(sendBuf, len, 0);

	if (this->msg_id++ < 0) this->msg_id = 1;
}
