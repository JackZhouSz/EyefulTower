// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

public partial class SlamMapContainer : ScrollContainer
{
    [Export]
    private bool PlaceableGoals = false;

    [Export]
    private SlamMapTexture SlamMap;

    [Export]
    private Texture2D SlamMapTexture;

    private bool validMouse = false;

    public override void _Ready()
    {
        base._Ready();
        SlamMap.CanPlaceGoals(PlaceableGoals);
        SlamMap.Texture = SlamMapTexture;
    }

    public SlamMapTexture GetSLAMMap()
    {
        return SlamMap;
    }

}
