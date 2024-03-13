﻿using System;
using System.ComponentModel;
using System.Globalization;

namespace IndustrialPark
{
    public class HexUShortTypeConverter : TypeConverter
    {
        public override bool CanConvertFrom(ITypeDescriptorContext context, Type sourceType)
        {
            return sourceType == typeof(string);
        }

        public override object ConvertFrom(ITypeDescriptorContext context, CultureInfo culture, object value)
        {
            if (value is string s)
            {
                return Convert.ToUInt16(s, 16);
            }

            return base.ConvertFrom(context, culture, value);
        }

        public override bool CanConvertTo(ITypeDescriptorContext context, Type destinationType)
        {
            return destinationType == typeof(ushort);
        }

        public override object ConvertTo(ITypeDescriptorContext context, CultureInfo culture, object value, Type destinationType)
        {
            if (destinationType == typeof(string))
            {
                if (value is uint vuint)
                    return vuint.ToString("X4");
                if (value is ushort vushort)
                    return vushort.ToString("X4");
            }

            return base.ConvertTo(context, culture, value, destinationType);
        }
    }
}